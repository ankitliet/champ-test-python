'''
: Container File
'''
from dependency_injector import containers, providers

from ..terrastate.resource import DatabaseResource
from .engine import Engine

class Container(containers.DeclarativeContainer):

    config = providers.Configuration()

    db = providers.Singleton(
        DatabaseResource, 
        db_url=config.DatabaseResource.url, 
        db_schema=config.DatabaseResource.schema
    )

    IPAMOps = providers.Factory(
        Engine,
        conf=config.Engine,
        db_conn=db,
        env_vars = config.ENV_VARS
    )