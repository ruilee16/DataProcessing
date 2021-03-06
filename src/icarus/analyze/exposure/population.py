
import logging as log
from typing import List, Dict

from icarus.analyze.exposure.network import Network
from icarus.analyze.exposure.event import Event
from icarus.analyze.exposure.leg import Leg
from icarus.analyze.exposure.activity import Activity
from icarus.analyze.exposure.types import LegMode, ActivityType
from icarus.analyze.exposure.agent import Agent
from icarus.util.general import defaultdict
from icarus.util.sqlite import SqliteUtil


def temp(table):
    return f'temp_{abs(hash(table))}'


class Population:
    def __init__(self, database: SqliteUtil, network: Network):
        self.database = database
        self.network  = network
        self.agents: Dict[str, Agent] = {}
        self.table = None


    def fetch_events(self):
        query = f'''
            SELECT
                output_events.event_id,
                output_legs.agent_id,
                output_legs.agent_idx,
                output_events.link_id,
                output_events.start,
                output_events.end
            FROM output_events
            INNER JOIN output_legs
            USING(leg_id)
            INNER JOIN {self.table}
            USING(agent_id)
            ORDER BY
                leg_id,
                leg_idx; '''
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()

    
    def fetch_legs(self):
        query = f'''
            SELECT
                leg_id,
                agent_id,
                agent_idx,
                mode,
                start,
                end
            FROM output_legs
            INNER JOIN {self.table}
            USING(agent_id); '''
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()


    def fetch_activities(self):
        query = f'''
            SELECT
                activity_id,
                agent_id,
                agent_idx,
                type,
                link_id,
                start,
                end
            FROM output_activities
            INNER JOIN {self.table}
            USING(agent_id); '''
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()

    
    def fetch_agents(self):
        query = f'''
            SELECT agent_id
            FROM output_agents
            INNER JOIN {self.table}
            USING(agent_id); '''
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()

    
    def load_events(self):
        events = self.fetch_events()
        for event_id, agent_id, agent_idx, link_id, start, end in events:
            link = self.network.links[link_id]
            event = Event(event_id, link, start, end)
            self.agents[agent_id].add_event(agent_idx, event)

    
    def load_legs(self):
        legs = self.fetch_legs()
        for leg_id, agent_id, _, mode, start, end in legs:
            leg = Leg(leg_id, LegMode(mode), start, end)
            self.agents[agent_id].add_leg(leg)

    
    def load_activities(self):
        activities = self.fetch_activities()
        for activity_id, agent_id, _, kind, link_id, start, end in activities:
            link = self.network.links[link_id]
            activity = Activity(activity_id, ActivityType(kind), link, start, end)
            self.agents[agent_id].add_activity(activity)


    def load_agents(self):
        agents = tuple(agent[0] for agent in self.fetch_agents())
        for agent_id in agents:
            self.agents[agent_id] = Agent(agent_id)


    def create_population(self, agents: List[str]):
        self.table = temp('population')
        self.database.drop_table(self.table)
        query = f'''
            CREATE TABLE {self.table} AS 
            SELECT agent_id 
            FROM output_agents
            WHERE agent_id in {tuple(agents)}; '''
        self.database.cursor.execute(query)
        query = f'''
            CREATE INDEX {self.table}_agent
            ON {self.table}(agent_id);   '''
        self.database.cursor.execute(query)
        self.database.connection.commit()

    
    def load_population(self):
        self.load_agents()
        self.load_activities()
        self.load_legs()
        self.load_events()

    
    def delete_population(self):
        if self.table is not None:
            self.database.drop_table(self.table)
            self.table = None
            self.agents = {}

    
    def calculate_exposure(self):
        for agent in self.agents.values():
            agent.calculate_exposure()


    def export_agents(self):
        for agent in self.agents.values():
            yield agent.export()

    
    def export_legs(self):
        for agent in self.agents.values():
            for idx, leg in enumerate(agent.legs):
                yield leg.export(agent.id, idx)

    
    def export_activities(self):
        for agent in self.agents.values():
            for idx, activity in enumerate(agent.activities):
                yield activity.export(agent.id, idx)

    
    def export_events(self):
        for agent in self.agents.values():
            for leg in agent.legs:
                for idx, event in enumerate(leg.events):
                    yield event.export(leg.id, idx)

    