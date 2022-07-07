'''
: Container File
'''
from dependency_injector import containers, providers

from .resource import DatabaseResource
from .engine import Engine
from util.core.app.models import AutomationRequest, AutomationTask,\
    AutomationPlan, AutomationCode


class Container(containers.DeclarativeContainer):

    config = providers.Configuration()

    db = providers.Singleton(
        DatabaseResource, 
        db_url=config.DatabaseResource.url, 
        db_schema=config.DatabaseResource.schema
    )
    
    AzureARM = providers.Factory(
        Engine,
        conf=config.Engine,
        db_conn=db,
        env_vars=config.ENV_VARS
    )