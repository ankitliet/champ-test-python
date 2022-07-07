import os
import yaml
from .resources import DatabaseResource
from .repositories import CommonRepository
from .services import CommonService
from util.core.app.models import ConfigAudit

def insert_config_audit(payload, session_factory=None):
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
                                                        ConfigAudit))
    #print("service = " + str(service))
    service.create(**payload)
