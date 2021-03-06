
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.util.print import PrintUtil as pr
from icarus.abm.parse.agents.parser import AgentsParser

parser = ArgumentParser(prog='AgentsParser',
    description='Parse ABM agents CSV file into table in a SQL database.')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'abm/parse/agents/config.json'),
    help=('Specify a config file location; default is "config.json" in '
        'the current working directory.'))
parser.add_argument('--log', type=str, dest='log',
    help='specify a log file location; by default the log will not be saved',
    default=None)
args = parser.parse_args()

if args.log is not None:
    pr.log(args.log)

try:
    with open(args.config) as handle:
        config = json.load(handle)
except FileNotFoundError as err:
    pr.print(f'Config file {args.config} not found.', time=True)
    raise err
except json.JSONDecodeError as err:
    pr.print(f'Config file {args.config} is not valid JSON.', time=True)
    raise err
except KeyError as err:
    pr.print(f'Config file {args.config} is not valid config file.', time=True)
    raise err

database = config['database']
encoding = config['encoding']

database['password'] = getpass(
    f'SQL password for {database["user"]}@localhost: ')

parser = AgentsParser(database, encoding)

if not config['resume']:
    for table in database['tables'].keys():
        parser.database.create_table(table)

options = ('silent', 'bin_size', 'resume')
params = {key:config[key] for key in options if key in config}

parser.parse(config['sourcepath'], **params)

if config['create_idxs']:
    parser.create_idxs()