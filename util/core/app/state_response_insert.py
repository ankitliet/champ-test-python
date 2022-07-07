import os
import yaml
from .models import States
from sqlalchemy import create_engine, orm
from sqlalchemy.orm import Session
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def insert_state_response(payload):
    config_file = os.path.join(os.environ['BASEDIR'],
                               'configurations',
                               f'{os.environ["EXECFILE"]}.yml')
    #config_file = "dev.yml"
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
    
    db_url = config.get('DatabaseResource').get('url')
    
    db_schema='terraform_remote_state'



    _engine = create_engine(
                            db_url, pool_size=20, max_overflow=15, echo=False,
                            pool_recycle=300, pool_pre_ping=True, pool_use_lifo=True,
                            connect_args={'options': '-csearch_path={}'.format(db_schema)}
                          )
    _session = orm.scoped_session(
                orm.sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=_engine,
                ),
            )

    body = States(**payload)
    _session.add(body)
    _session.commit()
    
