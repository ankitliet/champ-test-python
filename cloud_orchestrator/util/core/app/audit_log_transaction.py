import os
import yaml
from .resources import DatabaseResource
from .repositories import CommonRepository
from .services import CommonService
from .models import TransactionLog, Infracost
from copy import deepcopy

# GLOBALS
secrets = ['azure_client_secret', 'admin_password']


def recr_dict(tmp: dict):
    for key, value in tmp.items():
        if isinstance(value, dict):
            recr_dict(value)
        elif isinstance(value, list):
            recr_list(value)
        else:
            if key in secrets:
                tmp[key] = 'XXXX-SECRET-XXXX'


def recr_list(tmp: list):
    for value in tmp:
        if isinstance(value, dict):
            recr_dict(value)
        elif isinstance(value, list):
            recr_list(value)
        else:
            if value in secrets:
                index = tmp.index(value)
                tmp.pop(index)
                tmp.insert(index, 'XXXX-SECRET-XXXX')


def insert_infracost(payload, session_factory=None):
    if not session_factory:
        config_file = os.path.join(os.environ['BASEDIR'],
                                   'configurations',
                                   f'{os.environ["EXECFILE"]}.yml')
        if not os.path.exists(config_file):
            config_file = os.path.join(os.environ['BASEDIR'],
                                       'core', 'core', 'settings',
                                       f'{os.environ["EXECFILE"]}.yml')

        print("config_file = " + str(config_file))
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
        except Exception as ex:
            raise Exception("Config file not found:%s" % str(ex))
        print("config = " + str(config))
        db = DatabaseResource(
            db_url=config.get('db').get('url'),
            db_schema=config.get('db').get('schema')
        )
        session_factory = db.session
    service = CommonService(repository=CommonRepository(session_factory,
                                                        Infracost))
    service.create_or_update(**payload)


def insert_audit_log(payload, session_factory=None):
    if not session_factory:
        config_file = os.path.join(os.environ['BASEDIR'],
                                   'configurations',
                                   f'{os.environ["EXECFILE"]}.yml')
        # config_file = "dev.yml"
        if not os.path.exists(config_file):
            config_file = os.path.join(os.environ['BASEDIR'],
                                       'core', 'core', 'settings',
                                       f'{os.environ["EXECFILE"]}.yml')

        print("config_file = " + str(config_file))
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
        except Exception as ex:
            raise Exception("Config file not found:%s" % str(ex))
        print("config = " + str(config))
        db = DatabaseResource(
            db_url=config.get('db').get('url'),
            db_schema=config.get('db').get('schema')
        )
        session_factory = db.session
    # print("session_factory = " + str(session_factory))
    service = CommonService(repository=CommonRepository(session_factory,
                                                        TransactionLog))
    # print("service = " + str(service))

    #     payload = deepcopy(payload)
    #     recr_dict(payload)
    service.create(**payload)
