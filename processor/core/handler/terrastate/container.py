'''
: Container File
'''
from dependency_injector import containers, providers

from .resource import DatabaseResource
from .mapper import create_tf
from .engine import Engine, EngineStateMachine, ParallelEngine
from util.core.app.models import AutomationRequest, AutomationTask,\
    AutomationPlan, AutomationCode


class Container(containers.DeclarativeContainer):

    config = providers.Configuration()

    db = providers.Singleton(
        DatabaseResource, 
        db_url=config.DatabaseResource.url, 
        db_schema=config.DatabaseResource.schema
    )
    
    mapper = providers.Callable(
        create_tf
    )
    
    TerraState = providers.Factory(
        Engine,
        conf=config.Engine,
        mapper=mapper.provider,
        db_conn=db,
        env_vars=config.ENV_VARS
    )
    
    ParallelTerraAnsible = providers.Factory(
        ParallelEngine,
        conf=config.Engine,
        mapper=mapper.provider,
        db_conn=db,
        env_vars=config.ENV_VARS
    )
    
    engineFSM = providers.Factory(
        EngineStateMachine
    )