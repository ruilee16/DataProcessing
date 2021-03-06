
from  icarus.util.database import DatabaseUtil

class PlansParserDatabase(DatabaseUtil):
    def write_agents(self, agents):
        self.write_rows(agents, 'agents')

    def write_activities(self, activities):
        self.write_rows(activities, 'activities')

    def write_routes(self, routes):
        self.write_rows(routes, 'routes')