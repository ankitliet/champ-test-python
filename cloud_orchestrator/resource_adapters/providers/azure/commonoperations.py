
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from resource_adapters.utils.azure_clients import *
from util.core.app.logger import get_logger_func
LOG = get_logger_func(__file__)

def add_audit_log(session, task_id, source, event, trace, status):
    payload = {
        "task_id": task_id,
        "source": source,
        "event": event,
        "trace": trace,
        "status": status
    }
    LOG.debug("Insert audit logs:%s" % payload, {'task_id': task_id})
    insert_audit_log(payload, session_factory=session._session_factory)

############## Delete Resource Group #####################
#     Delete Storage container : When you delete a resource group, all of its resources are also deleted. 
#     Deleting a resource group deletes all of its template deployments and currently stored operations.
def delete_resource_group(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    resourcegroup_client = get_resourcegroup_client(parameters) # resource group client
    LOG.debug("Delete Resource Group:%s" % parameters, {'task_id': task_id})
    try:
        resource_group_name = parameters.get('resource_group_name')
    except Exception as e:
        raise Exception("Resource Group missing:%s" % str(e))
        
    add_audit_log(session, task_id, "CommonOperation", "delete resource group:%s"
                  % resource_group_name,
                  "started", TASK_STATUS.COMPLETED)
    async_resource_group_delete = resourcegroup_client.resource_groups.begin_delete(
        resource_group_name)
    async_resource_group_delete.wait()
    add_audit_log(session, task_id, "CommonOperation", "delete resource group:%s"
                  % resource_group_name,
                  "Success", TASK_STATUS.COMPLETED)

###################################
def delete_os_image(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    compute_client = get_compute_client(parameters)
    LOG.debug("Delete OS Image:%s" % parameters, {'task_id': task_id})
    image_name = parameters.get('image_name')
    add_audit_log(session, task_id, "CommonOperation", "delete os image:%s" % image_name,
                  "started", TASK_STATUS.COMPLETED)
    async_delete_image = compute_client.images.begin_delete(
        parameters.get('resource_group_name'), image_name)
    async_delete_image.wait()
    add_audit_log(session, task_id, "CommonOperation", "delete os image:%s" % image_name,
                  "Success", TASK_STATUS.COMPLETED)

def delete_route(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("Delete Route:%s" % parameters, {'task_id': task_id})
    route_name = parameters.get('route_name')
    route_table_name = parameters.get('route_table_name')
    add_audit_log(session, task_id, "CommonOperation", "delete Route:%s" % route_name,
                  "started", TASK_STATUS.COMPLETED)
    async_delete_route = network_client.routes.begin_delete(
        parameters.get('resource_group_name'), route_table_name,route_name)
    async_delete_route.wait()
    add_audit_log(session, task_id, "CommonOperation", "delete Route:%s" % route_name,
                  "Success", TASK_STATUS.COMPLETED)