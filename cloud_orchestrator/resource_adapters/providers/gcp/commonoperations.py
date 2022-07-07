from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from util.core.app.terraform_resource import TerraformClass
from google.cloud import compute_v1
from resource_adapters.utils.gcp_clients import *

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

def delete_os_image(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_os_image:%s" % parameters, {'task_id': task_id})
    image_name = parameters.get("image_name")
    add_audit_log(session, task_id, "CommonOperation",
                  "delete_os_image:%s" % image_name,
                  "started", TASK_STATUS.COMPLETED)

    image_client = get_gcp_image_client(parameters)
    op_client = get_gcp_op_client(parameters)
    op = image_client.delete(project=parameters.get('gcp_project'),
                             image=image_name)

    while op.status != compute_v1.Operation.Status.DONE:
        op = op_client.wait(
            operation=op.name, zone = parameters.get('zone'),
            project=parameters.get('gcp_project'))
    if op.http_error_status_code == 0:
        add_audit_log(session, task_id, "CommonOperation",
                      "delete_os_image:%s" % image_name,
                      "Success", TASK_STATUS.COMPLETED)
    else:
        add_audit_log(session, task_id, "CommonOperation",
                      "delete_os_image:%s" % image_name,
                      "{}-{}".format(op.http_error_status_code, op.http_error_message),
                      TASK_STATUS.FAILED)
        raise Exception("Failed to perform operation:%s" % str(op.http_error_message))

def delete_route(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    image_client = get_gcp_image_client(parameters)
    global_client = get_gcp_wait_client_global(parameters)
    LOG.debug("delete_os_image:%s" % parameters, {'task_id': task_id})
    route_name = parameters.get("route_name")
    add_audit_log(session, task_id, "CommonOperation",
                  "delete_route:%s" % route_name,
                  "started", TASK_STATUS.COMPLETED)

    op = image_client.delete(project=parameters.get('gcp_project'),
                             route=route_name)

    while op.status != compute_v1.Operation.Status.DONE:
        op = global_client.wait(operation=op.name,
                                project=parameters.get('gcp_project'))

    if op.http_error_status_code == 0:
        add_audit_log(session, task_id, "CommonOperation",
                      "delete_route:%s" % route_name,
                      "Success", TASK_STATUS.COMPLETED)
    else:
        add_audit_log(session, task_id, "CommonOperation", "delete_route:%s" % route_name,
                      "{}-{}".format(op.http_error_status_code, op.http_error_message),
                      TASK_STATUS.FAILED)
        raise Exception("Failed to perform operation:%s" % str(op.http_error_message))