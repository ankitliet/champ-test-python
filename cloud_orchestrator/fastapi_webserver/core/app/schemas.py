from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel, validator, Json
from enum import Enum


class TaskSchema(BaseModel):
    id: Optional[int] = None
    ref_id: Optional[str] = None
    action: Optional[str] = None
    source: Optional[str] = None
    parameters: Optional[dict] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    cloud_provider: Optional[str] = None


class UserSchema(BaseModel):
    username: str
    password: str


class Jeopardy(BaseModel):
    filters: dict


class CredentialSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    modified_by: Optional[str] = None


class SearchSchema(BaseModel):
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    cloud_provider: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    created_by: Optional[str] = None
    references: Optional[dict] = None
    parameters: Optional[dict] = None


class PlanSchema(BaseModel):
    id: Optional[int] = None
    execution_plan: Optional[dict] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    cloud_provider: Optional[str] = None
    name: Optional[str] = None
    input_schema: Optional[dict] = None


class AgentSchema(BaseModel):
    id: Optional[int] = None
    meta_data: Optional[dict] = None
    created_by: Optional[str] = None
    url: Optional[str] = None
    ip_address: Optional[str] = None
    node_name: Optional[str] = None


class CodeSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    cloud_provider: Optional[str] = None
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    cred_id: Optional[int] = None
    script_path: Optional[str] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None


class ApplicationSchema(BaseModel):
    id: Optional[int] = None
    source: Optional[str] = None
    description: Optional[str] = None
    secret_key: Optional[int]
    access_key: Optional[str] = None
    channel: Optional[dict] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    is_active: Optional[bool] = None
    encryption_key: Optional[str] = None
    encryption_iv: Optional[str] = None


class AutoTaskSchema(BaseModel):
    id: Optional[int] = None
    references: Optional[Dict] = None
    blueprint_name: Optional[str] = None
    cust_sub_id: Optional[int]
    source: Optional[str] = None
    parameters: Optional[dict] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    cloud_provider: Optional[str] = None
    task_id: Optional[str] = None


class ActionSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    jenkins_job: Optional[str] = None
    request_url: Optional[str] = None
    cloud_provider: Optional[str] = None


class ApiConfigSchema(BaseModel):
    id: Optional[int] = None
    task_name: Optional[str] = None
    application_name: Optional[str] = None
    cloud_provider: Optional[str] = None
    request_url: Optional[str] = None
    request_parameters_map: Optional[dict] = None
    response_parameters_map: Optional[dict] = None
    callback_url: Optional[str] = None
    credentials: Optional[str] = None
    request_parameters: Optional[dict] = None
    headers: Optional[dict] = None
    method: Optional[str] = None


class RequestTaskSchema(TaskSchema):
    ref_id: Optional[str]
    action: Optional[str]


class TerraformStates(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    data: Optional[str] = None

    class Config:
        orm_mode = True


class ResponseTaskSchema(TaskSchema):
    states: Optional[List[TerraformStates]]

    class Config:
        orm_mode = True


class Catalouge(BaseModel):
    task_name: Optional[str] = None
    cloud_provider: Optional[str] = None
    description: Optional[str] = None
    payload: Optional[dict] = None


class QueuesSchema(BaseModel):
    id: Optional[int] = None
    queue_name: Optional[str] = None
    exchange_key: Optional[str] = None
    is_default: Optional[bool] = False
    cloudorch_processor_id: Optional[int] = None


class ResourceAdapterMappingSchema(BaseModel):
    id: Optional[int] = None
    data: Optional[list] = None
    queue_id: Optional[int] = None


class ProductCategorySchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    status: Optional[bool] = None
    cloud_provider: Optional[str] = None


class ProductSubCategorySchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    status: Optional[bool] = None
    cloud_provider: Optional[str] = None
    product_category_id: Optional[int] = None


class ProductItemSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    status: Optional[bool] = True
    price: Optional[int] = None
    product_subcategory_id: Optional[int] = None
    cloud_provider: Optional[str] = None
    ui_layout: Optional[Dict] = None
    htc_marketplace: Optional[bool] = False
    cloud_marketplace: Optional[bool] = False
    logo_base64: Optional[bytes] = None


class LoginUserSchema(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class AppUserSchema(BaseModel):
    id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False
    created_by: Optional[str] = None
    modified_by: Optional[str] = None


class RolesSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None


class UserInRolesSchema(BaseModel):
    id: Optional[int] = None
    username: Optional[str] = None
    role_id: Optional[int] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None


class CallbackResponseSchema(BaseModel):
    status: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict] = None


class CloudCredentialsSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    cloud_provider: Optional[str] = None
    credentials: Optional[Dict] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None


class InfracostSchema(BaseModel):
    id: Optional[int] = None
    task_id: Optional[str] = None
    cost_json: Optional[Dict] = None


class CloudmasterSchema(BaseModel):
    credential_id: Optional[int] = None
    source: Optional[str] = None
    cloud_provider: Optional[str] = None
    credentials: Optional[Dict] = None
    task_name: Optional[str] = None
    parameters: Optional[Dict] = None


class OAuthProviderSchema(BaseModel):
    id: Optional[int] = None
    provider: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    config_url: Optional[str] = None
    app_home_url: Optional[str] = None
    app_error_url: Optional[str] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None


class ReportSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    report_url: Optional[str] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
