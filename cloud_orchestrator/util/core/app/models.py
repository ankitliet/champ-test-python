from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, Boolean, JSON, LargeBinary
from sqlalchemy.dialects.postgresql import JSON, DOUBLE_PRECISION
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class TransactionLog(Base):
    __tablename__ = 'transaction_log_audit'

    id = Column(Integer, primary_key=True)
    task_id = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    event = Column(String(255), nullable=False)
    trace = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(255), nullable=True)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class ConfigAudit(Base):
    __tablename__ = 'config_audit'

    Id = Column(Integer, primary_key=True)
    config_name = Column(String(255), nullable=False)
    operation_name = Column(String(255), nullable=False)
    config_value = Column(JSON, nullable=True)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = Column(String(255), nullable=False)
    modified_by = Column(String(255), nullable=True)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class TaskAction(Base):
    __tablename__ = 'task_action'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    jenkins_job = Column(String(255), nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String(255), nullable=False)
    cloud_provider = Column(String(255), nullable=True)
    input_schema = Column(String(2048), nullable=True)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class Credentials(Base):
    __tablename__ = 'credentials'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    password = Column(Text, nullable=True)
    ssh_key = Column(String(255), nullable=True)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class AutomationCode(Base):
    __tablename__ = 'automation_code'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True)
    cloud_provider = Column(String(255), nullable=True)
    repo_url = Column(String(255), nullable=True)
    branch = Column(String(255), nullable=True)
    cred_id = Column(Integer, ForeignKey(Credentials.id), nullable=False)
    script_path = Column(String(255), nullable=True)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    modified_by = Column(String(255), nullable=True)
    credentials = relationship("Credentials", primaryjoin="AutomationCode.cred_id==Credentials.id", lazy='joined')

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


def get_states_model():
    # Terraform state class
    class States(Base):
        __tablename__ = 'states'
        __table_args__ = {'schema': 'terraform_remote_state',
                          'extend_existing': True}

        id = Column(Integer, primary_key=True)
        name = Column(String(255), nullable=True)
        data = Column(JSON, nullable=True)

    return States


class TaskRequest(Base):
    __tablename__ = 'task_request'

    id = Column(Integer, primary_key=True)
    ref_id = Column(String(255), nullable=False)
    task_id = Column(String(255), nullable=False)
    action = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    parameters = Column(JSON, nullable=True)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)
    node_name = Column(String(255), nullable=True)
    build_id = Column(String(255), nullable=True)
    build_status = Column(String(255), nullable=True)
    created_by = Column(String(255), nullable=True)
    modified_by = Column(String(255), nullable=True)
    cloud_provider = Column(String(255), nullable=True)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class AutomationPlan(Base):
    __tablename__ = 'automation_plan'

    id = Column(Integer, primary_key=True)
    execution_plan = Column(JSON, nullable=True)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    modified_by = Column(String(255), nullable=True)
    cloud_provider = Column(String(255), nullable=True)
    task = relationship("AutomationTask", primaryjoin="AutomationPlan.id==AutomationTask.plan_id", lazy='joined')

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class ProcessorAgent(Base):
    __tablename__ = 'processor_agents'

    id = Column(Integer, primary_key=True)
    meta_data = Column(JSON, nullable=True)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    node_name = Column(String(255), nullable=False)
    ip_address = Column(String(255), nullable=False)
    url = Column(String(255), nullable=False)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class Application(Base):
    __tablename__ = 'application'

    id = Column(Integer, primary_key=True)
    source = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    secret_key = Column(String(255), nullable=True)
    access_key = Column(String(255), nullable=True)
    channel = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=True)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = Column(String(255), nullable=False)
    modified_by = Column(String(255), nullable=True)
    encryption_key = Column(String(255), nullable=True)
    encryption_iv = Column(String(255), nullable=True)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class AutomationTask(Base):
    __tablename__ = 'automation_task'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    task_name = Column(String(255), nullable=False)
    cloud_provider = Column(String(255), nullable=True)
    input_schema = Column(String(255), nullable=True)
    plan_id = Column(Integer, ForeignKey(AutomationPlan.id), nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)
    created_by = Column(String(255), nullable=False)
    modified_by = Column(String(255), nullable=True)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class AutomationRequest(Base):
    __tablename__ = 'automation_request'

    id = Column(Integer, primary_key=True)
    references = Column(JSON, nullable=False)
    task_id = Column(String(255), nullable=False)
    task_name = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    parameters = Column(JSON, nullable=True)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)
    status = Column(String(255), nullable=True)
    created_by = Column(String(255), nullable=True)
    modified_by = Column(String(255), nullable=True)
    cloud_provider = Column(String(255), nullable=True)
    rollback = Column(Boolean, default=False)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class StateTransitionLog(Base):
    __tablename__ = 'state_transition_log'

    id = Column(Integer, primary_key=True)
    plan_id = Column(String(255), nullable=True)
    current_state = Column(String(255), nullable=True)
    current_status = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=True)
    created_timestamp = Column(DateTime, nullable=True, default=datetime.utcnow)
    kv_log = Column(Text, nullable=True)
    identifier = Column(String(255), nullable=True)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class WorkBench(Base):
    __tablename__ = 'test_workbench'

    id = Column(Integer, primary_key=True)
    task_name = Column(String(255), nullable=False)
    cloud_provider = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    payload = Column(JSON, nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class States(Base):
    __tablename__ = 'states'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    data = Column(Text, nullable=False)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class DBConfigModel(Base):
    __tablename__ = 'system_config'

    id = Column(Integer, primary_key=True)
    key = Column(String(255))
    value = Column(String(255))
    created_date = Column(DateTime, nullable=True, default=datetime.utcnow)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class TerraformPlan(Base):
    __tablename__ = 'terraform_plan'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, nullable=False)
    plan = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=True)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_by = Column(String(255), nullable=True)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class Queues(Base):
    __tablename__ = 'queues'

    id = Column(Integer, primary_key=True)
    queue_name = Column(String(50), nullable=True)
    exchange_key = Column(String(50), nullable=True)
    is_default = Column(Boolean, default=False)
    cloudorch_processor_id = Column(Integer, nullable=True)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class ResourceAdapterMapping(Base):
    __tablename__ = 'resource_adapter_mapping'

    id = Column(Integer, primary_key=True)
    cloud_provider = Column(String(50), nullable=False)
    queue_id = Column(Integer, nullable=True)
    screen_name = Column(String(50), nullable=True)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class DefaultConfig(Base):
    __tablename__ = 'task_config'

    id = Column(Integer, primary_key=True)
    cloud_provider = Column(String(255), nullable=False)
    task_name = Column(String(255), nullable=False)
    default_values = Column(JSON, nullable=False)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class APIConfig(Base):
    __tablename__ = 'api_configurations'

    id = Column(Integer, primary_key=True)
    cloud_provider = Column(String(255), nullable=False)
    task_name = Column(String(255), nullable=False)
    application_name = Column(String(255), nullable=False)
    request_url = Column(String(255), nullable=False)
    callback_url = Column(String(255), nullable=False)
    credentials = Column(String(1024), nullable=False)
    request_parameters = Column(JSON, nullable=False)
    request_parameters_map = Column(JSON, nullable=False)
    response_parameters_map = Column(JSON, nullable=False)
    headers = Column(JSON, nullable=False)
    method = Column(String(255), nullable=False)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'

    def _asdict(self, exclude_list=[]):
        _dict = dict(self.__dict__)
        exclude_list.append('_sa_instance_state')
        for key in exclude_list:
            _dict.pop(key, None)
        return _dict


class ProductCategory(Base):
    __tablename__ = 'product_category'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    created_by = Column(String(255), nullable=False)
    created_date = Column(String(255), nullable=False, default=datetime.utcnow)
    modified_by = Column(String(255), nullable=False)
    modified_date = Column(String(255), nullable=False, default=datetime.utcnow)
    status = Column(Boolean, nullable=True)
    cloud_provider = Column(String(255), nullable=False)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class ProductSubCategory(Base):
    __tablename__ = 'product_subcategory'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    created_by = Column(String(255), nullable=False)
    created_date = Column(String(255), nullable=False, default=datetime.utcnow)
    modified_by = Column(String(255), nullable=False)
    modified_date = Column(String(255), nullable=False, default=datetime.utcnow)
    status = Column(Boolean, nullable=True)
    product_category_id = Column(String(255), nullable=False)
    cloud_provider = Column(String(255), nullable=False)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class ProductItems(Base):
    __tablename__ = 'product_items'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    status = Column(Boolean, nullable=True)
    price = Column(DOUBLE_PRECISION, nullable=False)
    product_subcategory_id = Column(Integer, nullable=False)
    ui_layout = Column(JSON, nullable=False)
    cloud_provider = Column(String(255), nullable=False)
    htc_marketplace = Column(Boolean, nullable=False, default=False)
    cloud_marketplace = Column(Boolean, nullable=False, default=True)
    logo_base64 = Column(LargeBinary, nullable=False)
    created_by = Column(String(255), nullable=False)
    created_date = Column(String(255), nullable=False, default=datetime.utcnow)
    modified_by = Column(String(255), nullable=False)
    modified_date = Column(String(255), nullable=False, default=datetime.utcnow)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class ProductItem(Base):
    __tablename__ = 'product_items'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    status = Column(Boolean, nullable=True)
    price = Column(DOUBLE_PRECISION, nullable=False)
    product_subcategory_id = Column(Integer, nullable=False)
    ui_layout = Column(JSON, nullable=False)
    cloud_provider = Column(String(255), nullable=False)
    htc_marketplace = Column(Boolean, nullable=False, default=False)
    cloud_marketplace = Column(Boolean, nullable=False, default=True)
    logo_base64 = Column(LargeBinary, nullable=False)
    created_by = Column(String(255), nullable=False)
    created_date = Column(String(255), nullable=False, default=datetime.utcnow)
    modified_by = Column(String(255), nullable=False)
    modified_date = Column(String(255), nullable=False, default=datetime.utcnow)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class AppUser(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email_address = Column(String(255), nullable=False)
    user_name = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=True, default=True)
    is_admin = Column(Boolean, nullable=True, default=False)
    created_by = Column(String(255), nullable=False)
    modified_by = Column(String(255), nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class Roles(Base):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=True)
    # userinrole_id = Column(Integer, ForeignKey(UserInRoles.id), nullable=False)
    # users_in_roles = relationship("UserInRoles", primaryjoin="Roles.id==UserInRoles.role_id", lazy='joined')
    created_by = Column(String(255), nullable=False)
    modified_by = Column(String(255), nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class UserInRoles(Base):
    __tablename__ = 'user_roles'

    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey(Roles.id), nullable=False)
    # roles_details = Column(Integer, ForeignKey(Roles.id), nullable=False)
    roles_details = relationship("Roles", primaryjoin="Roles.id==UserInRoles.role_id", lazy='joined')
    created_by = Column(String(255), nullable=False)
    modified_by = Column(String(255), nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class CloudCredentials(Base):
    __tablename__ = 'cloud_credentials'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    cloud_provider = Column(String(255), nullable=False)
    credentials = Column(JSON, nullable=False)
    created_by = Column(String(255), nullable=False)
    modified_by = Column(String(255), nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class Infracost(Base):
    __tablename__ = 'infracost'

    id = Column(Integer, primary_key=True)
    task_id = Column(String(255), nullable=False)
    cost_json = Column(JSON, nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class OAuthProvider(Base):
    __tablename__ = 'oauth_provider'

    id = Column(Integer, primary_key=True)
    provider = Column(String(255), nullable=False)
    client_id = Column(String(1000), nullable=False)
    client_secret = Column(String(1000), nullable=False)
    config_url = Column(String(1000), nullable=False)
    app_home_url = Column(String(1000), nullable=False)
    app_error_url = Column(String(1000), nullable=False)
    created_by = Column(String(255), nullable=False)
    modified_by = Column(String(255), nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'


class Reports(Base):
    __tablename__ = 'reports'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=False)
    report_url = Column(String(1000), nullable=False)
    created_by = Column(String(255), nullable=False)
    modified_by = Column(String(255), nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)

    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'
