# GENERATING LOGGER for `base`
from logger import getlogger
logger = getlogger(__file__)

'''
    : ARGS parser file. Parse all the command for sage and worker.

    : Imports
        : External Imports:
            : argparse
            : pathlib.Path
            : os
            : uvicorn
'''
import argparse
import platform
from pathlib import Path
import os
import sys
import gflags

parent_parser = argparse.ArgumentParser(add_help=False)
parent_parser.add_argument("-r", "--release",
                           help="Input release enviorment of server - This must match with the `.yml` file present in "
                                "configurations folder",
                           default='local')
parent_parser.add_argument("-l", "--loglevel",
                           help="Input the log level",
                           default='DEBUG')
mainparser = argparse.ArgumentParser()
service_subparsers = mainparser.add_subparsers(dest='action')

worker_parser = service_subparsers.add_parser('startworker',
                                              help='Command to start worker. Provide appropirate flags for worker',
                                              parents=[parent_parser])
worker_parser.add_argument("-q", "--queue", help="Input name of worker to be started", default='teraform')
worker_parser.add_argument("--proxy-enabled", default=False, type=bool, help="Enabled/Disabled Proxy")


args = mainparser.parse_args()
os.environ['EXECFILE'] = args.release
os.environ['LOGLEVEL'] = args.loglevel.upper()
os.environ['BASEDIR'] = os.path.abspath(Path(__file__).resolve().parent)
os.environ['BASENAME'] = os.path.basename(Path(__file__).resolve().parent)
os.environ['PROXY_ENABLED'] = str(args.proxy_enabled)
os.environ['RABBITQUEUENAME'] = args.queue

sys.path.insert(0, os.path.abspath(Path(__file__).resolve().parent))
sys.path.insert(0, os.path.abspath(Path(__file__).resolve().parent.parent))



from util.core.app import constants

if platform.system() == "Windows":
    log_path = "{}\\Documents\\logs\\lws.log".format(Path.home())
else:
    log_path = "/var/log/logtest.log"

if platform.system() == "Windows":
    log_location = "{}\\Documents\\logs\\processor".format(Path.home())
else:
    log_location = "/mnt/logs/processor"

FLAGS = gflags.FLAGS
FLAGS.log_location = log_location
FLAGS.log_file = "processor.log"
FLAGS.log_level = "DEBUG"

    
if __name__ == '__main__':
    logger.info(f'initiating action[{args.action}]')
    if args.action == 'startworker':
        from container import ServerContainer
        _container = ServerContainer()
        _container.configuration.from_yaml(os.path.join(os.environ['BASEDIR'], 'configurations', f'{os.environ["EXECFILE"]}.yml'))
        _engine = _container.engine()
        _engine.initiate()
        
        logger.info(f'shuting down service...')
        db_session = _container.db_session()
        db_session._engine.dispose()