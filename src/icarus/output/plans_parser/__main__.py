
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.output.plans_parser.parser import PlansParser
from icarus.util.print import Printer as pr

parser = ArgumentParser(prog='AgentsParser',
    description='Parses MATSim output plans into SQL database.')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'output/plans_parser/config.json'),
    help=('Specify a config file location; default is "config.json" in '
        'the current working directory.'))
parser.add_argument('--log', type=str, dest='log',
    help='Specify a log file location; by default the log will not be saved.',
    default=None)
args = parser.parse_args()

try:
    if args.log is not None:
        pr.log(args.log)

    with open(args.config) as handle:
        config = json.load(handle)

    database = config['database']
    encoding = config['encoding']

    database['password'] = getpass(
        f'SQL password for {database["user"]}@localhost: ')

    parser = PlansParser(database, encoding)

    if not config['resume']:
        for table in database['tables'].keys():
            parser.database.create_table(table)

    options = ('silent', 'bin_size', 'resume')
    params = {key:config[key] for key in options if key in config}

    parser.parse(config['filepath'], **params)

    if config['create_idxs']:
        parser.index()

    if config['verify']:
        parser.verify()

except FileNotFoundError as err:
    print(f'Config file {args.config} not found.')
    raise(err)
except json.JSONDecodeError as err:
    print(f'Config file {args.config} is not valid JSON.')
    raise(err)
except KeyError as err:
    print(f'Config file {args.config} is not valid config file.')
    raise(err)
except Exception as err:
    raise(err)