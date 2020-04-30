
# from __future__ import annotations

import logging as log
from typing import List
from xml.etree.ElementTree import iterparse, tostring

from icarus.parse.events.types import LegMode
from icarus.parse.events.agent import Agent

from icarus.util.general import defaultdict, counter
from icarus.util.file import multiopen


class Route:
    __slots__= ('start_link', 'end_link', 'path', 'distance', 'mode')

    def __init__(self, start_link, end_link, path, 
            distance: float, mode: LegMode):
        self.start_link = start_link
        self.end_link = end_link
        self.path = path
        self.distance = distance
        self.mode = mode

    def get_exposure(self, start, stop):  
        exposure = 0
        duration = stop - start
        time = start
        distance = sum(link.length for link in self.path)
        for link in self.path:
            elapse = duration * link.length / distance
            exp = link.get_exposure(time, time + elapse)
            exposure += exp
            time += elapse
        return exposure



class Link:
    __slots__ = ('id', 'x', 'y', 'length', 'freespeed', 'centroid')

    def __init__(self, uuid: str, x: float, y:float, length: float, 
            freespeed: float, centroid):
        self.id = uuid
        self.x = x
        self.y = y
        self.length = length
        self.freespeed = freespeed
        self.centroid = centroid
    

    def get_temperature(self, time):
        return self.centroid.get_temperature(time)


    def get_exposure(self, start, stop):
        return self.centroid.get_exposure(start, stop)


    def entry(self):
        return (self.x, self.y, self.x, self.y)



class Centroid:
    __slots__ = ('id', 'x', 'y', 'temperatures')

    def __init__(self, uuid, x, y, temperatures):
        self.id = uuid
        self.x = x
        self.y = y
        self.temperatures = temperatures


    def get_temperature(self, time):
        steps = len(self.temperatures)
        step = int(time / 86400 * steps) % steps
        return self.temperatures[step]


    def get_exposure(self, start, stop):
        steps = len(self.temperatures)
        step_size = int(86400 / steps)
        start_step = int(start / 86400 * steps)
        stop_step = int(stop / 86400 * steps)
        exposure = 0
        if start_step == stop_step:
            exposure = (stop - start) * self.temperatures[start_step % steps]
        else:
            exposure = ((start_step + 1) * step_size - start) * \
                self.temperatures[start_step % steps]
            for step in range(start_step + 1, stop_step):
                exposure += step_size * self.temperatures[step % steps]
            exposure += (stop - stop_step * step_size) * \
                self.temperatures[stop_step % steps]
        return exposure



class Network:
    def __init__(self, database):
        self.database = database
        self.temperatures = defaultdict(lambda x: [])
        self.agents = {}
        self.links = {}
        self.centroids = {}


    def fetch_temperatures(self):
        self.database.cursor.execute('''
            SELECT
                temperature_id,
                temperature_idx,
                temperature
            FROM temperatures
            ORDER BY
                temperature_id,
                temperature_idx;  ''')
        return self.database.cursor.fetchall()


    def fetch_links(self):
        self.database.cursor.execute('''
            SELECT
                links.link_id,
                links.length,
                links.freespeed,
                links.modes,
                nodes.point,
                nodes.centroid_id
            FROM links
            INNER JOIN nodes
            ON links.source_node = nodes.node_id; ''')
        return self.database.cursor.fetchall()

    
    def fetch_centroids(self):
        self.database.cursor.execute('''
            SELECT
                centroid_id,
                temperature_id,
                center
            FROM centroids; ''')
        return self.database.cursor.fetchall()


    def get_agent(self, agent_id):
        agent = None
        if agent_id in self.agents:
            agent = self.agents[agent_id]
        else:
            agent = Agent(agent_id)
            self.agents[agent_id] = agent
        return agent

    
    def load_routes(self, planspath):
        plansfile = multiopen(planspath, mode='rb')
        plans = iter(iterparse(plansfile, events=('start', 'end')))
        evt, root = next(plans)

        agent = None
        selected = False
        mode = None
        count = 0
        n = 1

        for evt, elem in plans:
            if evt == 'start':
                if elem.tag == 'person':
                    agent = elem.get('id')
                elif elem.tag == 'plan':
                    selected = elem.get('selected') == 'yes'
                elif elem.tag == 'leg':
                    mode = elem.get('mode')
            elif evt == 'end':
                if elem.tag == 'route' and selected:
                    vehicle = elem.get('vehicleRefId')
                    kind = elem.get('type')
                    if vehicle == 'null' and kind == 'links':
                        start = elem.get('start_link')
                        end = elem.get('end_link')
                        distance = float(elem.get('distance'))
                        path = (self.links[link] for link in elem.text.split(' '))
                        uuid = f'{mode}-{start}-{end}'
                        route = Route(self.links[start], self.links[end], 
                            tuple(path), distance, LegMode(mode))
                        self.get_agent(agent).routes[uuid] = route
                elif elem.tag == 'person':
                    count += 1
                    if count % 10000 == 0:
                        root.clear()
                    if count == n:
                        log.info(f'Processing plan {count}.')
                        n <<= 1

        if count != (n >> 1):
            log.info(f'Processing plan {count}.')
        plansfile.close()

    
    def load_network(self, planspath):
        log.info('Fetching network temperatures from database.')
        temperatures = counter(self.fetch_temperatures(), 'Loading temperature %s.')

        log.info('Loading network temperatures.')
        for uuid, _, temperature in temperatures:
            self.temperatures[uuid].append(temperature)
        self.temperatures.lock()
        
        log.info('Fetching network centroids from database.')
        centroids = counter(self.fetch_centroids(), 'Loading centroid %s.')

        log.info('Loading network centroids.')
        for uuid, tempid, centroid in centroids:
            x, y = map(float, centroid[7:-1].split(' '))
            self.centroids[uuid] = Centroid(uuid, x, y, self.temperatures[tempid])

        log.info('Fetching network links from database.')
        links = counter(self.fetch_links(), 'Loading link %s.')

        log.info('Loading netowrk links.')
        for uuid, length, speed, _, point, centid in links:
            x, y = map(float, point[7:-1].split(' '))
            centroid = self.centroids[centid]
            self.links[uuid] = Link(uuid, x, y, length, speed, centroid)

        log.info('Loading network routes from output plans file.')
        self.load_routes(planspath)


    def get_temperature(self, link, time):
        return self.links[link].get_temperature(time)

        
    def get_exposure(self, link, start, stop):
        return self.links[link].get_exposure(start, stop)
