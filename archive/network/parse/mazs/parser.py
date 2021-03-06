
import shapefile

from xml.etree.ElementTree import iterparse

from icarus.network.parse.mazs.parser import MazParserDatabase
from icarus.util.print import PrintUtil as pr

class MazParser:
    def __init__(self, database):
        self.database = MazParserDatabase(database)

    @staticmethod
    def encode_poly(poly):
        if len(poly) == 0:
            return None
        if poly[0] != poly[-1]:
            poly.append(poly[0])
        return 'POLYGON((' + ','.join(str(pt[0]) + ' ' +
                str(pt[1]) for pt in poly) + '))'

    def parse_mazs(self, filepath, bin_size=10000):
        pr.print(f'Beginning network MAZ parsing from {filepath}.', time=True)
        pr.print('MAZ Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=0)

        parser = shapefile.Reader(filepath)
        target = len(parser)
        mazs = []
        count = 0
        
        for item in parser:
            mazs.append((
                item.record.MAZ_ID_10,
                item.record.TAZ_2015,
                item.record.Sq_miles,
                self.encode_poly(item.shape.points)))
            count += 1
            if count % bin_size == 0:
                pr.print(f'Pushing {bin_size} MAZs to database.', time=True)
                self.database.push_mazs(mazs)
                mazs = []
                pr.print('Resuming MAZ parsing.', time=True)
                pr.print('MAZ Parsing Progress', persist=True, replace=True,
                    frmt='bold', progress=count/target)

        pr.print(f'Pushing {count % bin_size} MAZs to database.', time=True)
        self.database.push_mazs(mazs)
        pr.print('MAZ Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=1)
        pr.push()
        pr.print('Network MAZ parsing complete.', time=True)
        