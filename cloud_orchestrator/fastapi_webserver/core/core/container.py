'''
: Container File
'''
from dependency_injector import containers, providers
from core.handlers.jenkins_handler.jenkinservice import JenkinsService
from core.handlers.jenkins_handler.queuehandler import MessageQueue
from core.utils.Authenticator import Authenticator
from .resources import DatabaseResource
from core.app.services import *
from core.app.repositories import *
from util.core.app.models import *
from ..app.repositories import CommonRepository
from ..app.services import CommonService


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    db = providers.Singleton(
        DatabaseResource,
        db_url=config.db.url,
        db_schema=config.db.schema
    )

    authentication_service = providers.Singleton(
        Authenticator,
        config=config
    )

    terraform_db = providers.Singleton(
        DatabaseResource,
        db_url=config.terraform_db.url,
        db_schema=config.terraform_db.schema
    )

    jenkins_service = providers.Singleton(
        JenkinsService,
        config=config.jenkins,
    )

    rmq_service = providers.Singleton(
        MessageQueue,
        config=config.rmq
    )

    task_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=TaskRequest
    )

    auto_task_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=AutomationRequest
    )
    auto_action_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=AutomationTask
    )

    auto_plan_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=AutomationPlan
    )

    auto_code_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=AutomationCode
    )

    cred_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=Credentials
    )

    workbench_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=WorkBench
    )

    audit_log_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=TransactionLog
    )

    audit_config_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=ConfigAudit
    )

    state_trans_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=StateTransitionLog
    )

    agent_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=ProcessorAgent
    )

    action_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=TaskAction
    )

    application_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=Application
    )

    states_repository = providers.Factory(
        CommonRepository,
        session_factory=terraform_db.provided.session,
        model=States
    )

    dbconfig_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=DBConfigModel
    )

    dbconfig_service = providers.Factory(
        CommonService,
        repository=dbconfig_repository
    )

    task_service = providers.Factory(
        CommonService,
        repository=task_repository
    )

    auto_task_service = providers.Factory(
        CommonService,
        repository=auto_task_repository
    )

    auto_action_service = providers.Factory(
        CommonService,
        repository=auto_action_repository
    )

    auto_plan_service = providers.Factory(
        CommonService,
        repository=auto_plan_repository
    )

    auto_code_service = providers.Factory(
        CommonService,
        repository=auto_code_repository
    )

    cred_service = providers.Factory(
        CommonService,
        repository=cred_repository
    )

    workbench_service = providers.Factory(
        CommonService,
        repository=workbench_repository
    )

    audit_log_service = providers.Factory(
        CommonService,
        repository=audit_log_repository
    )

    audit_config_service = providers.Factory(
        CommonService,
        repository=audit_config_repository
    )

    state_trans_service = providers.Factory(
        CommonService,
        repository=state_trans_repository
    )

    agent_service = providers.Factory(
        CommonService,
        repository=agent_repository
    )

    action_service = providers.Factory(
        CommonService,
        repository=action_repository
    )

    application_service = providers.Factory(
        CommonService,
        repository=application_repository
    )

    states_service = providers.Factory(
        CommonService,
        repository=states_repository
    )

    queues_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=Queues
    )

    default_config_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=DefaultConfig
    )

    api_config_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=APIConfig
    )

    api_config_service = providers.Factory(
        CommonService,
        repository=api_config_repository
    )

    default_config_service = providers.Factory(
        CommonService,
        repository=default_config_repository
    )

    queues_service = providers.Factory(
        CommonService,
        repository=queues_repository
    )

    resource_adapter_mapping_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=ResourceAdapterMapping
    )

    resource_adapter_mapping_service = providers.Factory(
        CommonService,
        repository=resource_adapter_mapping_repository
    )

    product_category_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=ProductCategory
    )

    product_category_service = providers.Factory(
        CommonService,
        repository=product_category_repository
    )

    product_subcategory_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=ProductSubCategory
    )

    product_subcategory_service = providers.Factory(
        CommonService,
        repository=product_subcategory_repository
    )

    product_item_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=ProductItem
    )

    product_item_service = providers.Factory(
        CommonService,
        repository=product_item_repository
    )

    product_items_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=ProductItems
    )

    product_items_service = providers.Factory(
        CommonService,
        repository=product_items_repository
    )

    user_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=AppUser
    )

    user_service = providers.Factory(
        CommonService,
        repository=user_repository
    )

    roles_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=Roles
    )

    role_service = providers.Factory(
        CommonService,
        repository=roles_repository
    )

    user_role_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=UserInRoles
    )

    user_role_service = providers.Factory(
        CommonService,
        repository=user_role_repository
    )

    cloud_cred_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=CloudCredentials
    )

    cloud_cred_service = providers.Factory(
        CommonService,
        repository=cloud_cred_repository
    )

    infracost_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=Infracost
    )

    infracost_service = providers.Factory(
        CommonService,
        repository=infracost_repository
    )

    oauth_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=OAuthProvider
    )

    oauth_service = providers.Factory(
        CommonService,
        repository=oauth_repository
    )

    report_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=Reports
    )

    report_service = providers.Factory(
        CommonService,
        repository=report_repository
    )
