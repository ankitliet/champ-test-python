strict=True# TODOD 
# 1. TYPING HINTS AND COMMENTS

from dependency_injector import containers, providers

from factories import *
from util.core.app.models import *
from core.operation.repositories import *
from core.operation.services import *
from resources import ThreadExecutorResource, DatabaseResource
from consumer.core.app.consumer import Consumer
from core.engine import Engine
import os




class ServerContainer(containers.DeclarativeContainer):

    # configuration provider
    configuration = providers.Configuration(strict=True)
    
    
    # resources
    thread_executor = providers.Resource(
        ThreadExecutorResource,
        max_workers=configuration.ThreadExecutorResource.max_workers,
        thread_name_prefix=configuration.ThreadExecutorResource.thread_name_prefix,
        initializer=configuration.ThreadExecutorResource.initializer,
        initargs=configuration.ThreadExecutorResource.initargs
    )
    
    db_session = providers.Singleton(
        DatabaseResource,
        db_url=configuration.DatabaseResource.url,
        db_schema=configuration.DatabaseResource.schema
    )
    
    
    # operation.repositories
    state_transition_log_repository = providers.Factory(
        CommonRepository,
        session_factory=db_session.provided.session,
        model=StateTransitionLog
    )
    
    request_repository = providers.Factory(
        CommonRepository,
        session_factory=db_session.provided.session,
        model=AutomationRequest
    )
    
    
    # operation.services
    state_transition_log_service = providers.Factory(
        StateTransitionLogService,
        repository=state_transition_log_repository
    )
    
    request_service = providers.Factory(
        CommonService,
        repository=request_repository
    )
    
    
    #listners
    rabbit_listner = providers.Factory(
        Consumer,
        config=configuration.rabbit_listner,
        queue_name=os.environ.get('RABBITQUEUENAME'),
        session=db_session.provided.session
    )
    
    
    # engine
    engine = EngineFactoryProvider(
        Engine,
        Engine=configuration.Engine,
        executor=thread_executor,
        state_transition_log_service=state_transition_log_service,
        request_service=request_service,
        rabbit_listner=rabbit_listner,
        session_factory=db_session.provided.session
    )