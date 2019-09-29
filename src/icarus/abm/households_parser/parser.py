
import csv

from icarus.abm.households_parser.database import HouseholdsParserDatabase
from icarus.util.print import Printer as pr

class HouseholdsParser:
    def __init__(self, database, encoding):
        self.database = HouseholdsParserDatabase(database)
        self.encoding = encoding

    def parse(self, sourcepath, resume=False, silent=False, bin_size=100000):
        if not silent:
            pr.print(f'Beginning ABM household data parsing from {sourcepath}',
                time=True)
            pr.print(f'Loading process metadata and resources.', time=True)

        target = sum(1 for l in open(sourcepath, 'r')) - 1
        tripsfile = open(sourcepath, 'r', newline='')
        parser = csv.reader(tripsfile, delimiter=',', quotechar='"')
        top = next(parser)
        cols = {key: val for key, val in zip(top, range(len(top)))}

        households = []
        hhid = 0

        if not silent:
            pr.print('Starting households CSV file iteration.', time=True)
            pr.print('Households Parsing Progress', persist=True, replace=True,
                frmt='bold', progress=hhid/target)
        
        for household in parser:
            households.append((
                int(household[cols['hhid']]),
                float(household[cols['pumsSerialNo']]),
                int(household[cols['homeTaz']]),
                int(household[cols['homeMaz']]),
                int(household[cols['hhsize']]),
                int(household[cols['numFtWorkers']]),
                int(household[cols['numPtWorkers']]),
                int(household[cols['numUnivStuds']]),
                int(household[cols['numNonWorkers']]),
                int(household[cols['nunmRetired']]),
                int(household[cols['numDrivAgeStuds']]),
                int(household[cols['numPreDrivStuds']]),
                int(household[cols['numPreshcool']]),
                int(household[cols['hhIncomeDollars']]),
                int(household[cols['hhNumAutos']]),
                int(household[cols['dwellingType']]),
                int(household[cols['ifAvHousehold']])))
            hhid += 1

            if hhid % bin_size == 0:
                if not silent:
                    pr.print(f'Pushing {bin_size} households to database.',
                        time=True)
                self.database.write_households(households)
                households = []
                if not silent:
                    pr.print('Resuming household CSV file parsing.', time=True)
                    pr.print('Household Parsing Progress', persist=True,
                        replace=True, frmt='bold', progress=hhid/target)

        if not silent:
            pr.print(f'Pushing {hhid % bin_size} households to database.', time=True)
        self.database.write_households(households)
        if not silent:
            pr.print('ABM household data parsing complete.', time=True)
            pr.print('Household Parsing Progress', persist=True, replace=True,
                frmt='bold', progress=1)
            pr.push()

    def create_idxs(self, silent=False):
        if not silent:
            pr.print(f'Creating all indexes in database {self.database.db}.', time=True)
        for tbl in self.database.tables:
            self.database.create_all_idxs(tbl)
        if not silent:
            pr.print(f'Index creating complete.', time=True)
                    
