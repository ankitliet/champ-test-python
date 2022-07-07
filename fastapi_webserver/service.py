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
import logging
import sys
import gflags
import urllib3
import uvicorn

parent_parser = argparse.ArgumentParser(add_help=False)
parent_parser.add_argument("-r", "--release",
                           help="Input release enviorment of server - This must match with the `.yml` file present in "
                                "configurations folder",
                           default='local')
parent_parser.add_argument("-t", "--telemetry", help="Specify if telemetry needs to be enabled", default='false')

mainparser = argparse.ArgumentParser()
service_subparsers = mainparser.add_subparsers(dest='action')

worker_parser = service_subparsers.add_parser('startworker',
                                              help='Command to start worker. Provide appropirate flags for worker',
                                              parents=[parent_parser])
worker_parser.add_argument("--host", help="Input name of worker to be started", default='0.0.0.0')
worker_parser.add_argument("--port", help="Input name of application to serve", default='8082')

args = mainparser.parse_args()
os.environ['EXECFILE'] = args.release
os.environ['TELEMETRY'] = args.telemetry
os.environ['BASEDIR'] = os.path.abspath(Path(__file__).resolve().parent)
os.environ['BASENAME'] = os.path.basename(Path(__file__).resolve().parent)

sys.path.insert(0, os.path.abspath(Path(__file__).resolve().parent))
sys.path.insert(0, os.path.abspath(Path(__file__).resolve().parent.parent))


if platform.system() == "Windows":
    LOG_PATH = "{}\\Documents\\logs\\lws.log".format(Path.home())
else:
    LOG_PATH = "/var/log/logtest.log"

if platform.system() == "Windows":
    log_location = "{}\\Documents\\logs\\webserver".format(Path.home())
else:
    log_location = "/mnt/logs/webserver"

#FLAGS = gflags.FLAGS
#FLAGS.log_location = log_location
#FLAGS.log_file = "webserver.log"
#FLAGS.log_level = "DEBUG"

if args.action == 'startworker':
    if __name__ == '__main__':
        print(f'Execution Env -> {args.release}')
        urllib3.disable_warnings()
        #log_config = uvicorn.config.LOGGING_CONFIG
        #log_config["formatters"]["access"]["fmt"] = \
        #    "%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s resource.service.name=%(otelServiceName)s] - %(message)s"
        uvicorn.run(
            "core.core.main:app",
            host=args.host,
            port=int(args.port),
            reload=False,
            debug=True,
            log_level=logging.DEBUG,
            #log_config=log_config,
            ssl_keyfile="{}/localhost.key".format(os.path.abspath(Path(__file__).resolve().parent)),
            ssl_certfile="{}/localhost.crt".format(os.path.abspath(Path(__file__).resolve().parent))
            #log_config=logging.basicConfig(
            #    filename=log_path,
            #    filemode='w',
            #    level=logging.DEBUG,
            #    format='%(asctime)s %(levelname)s %(message)s'
            #)
        )
