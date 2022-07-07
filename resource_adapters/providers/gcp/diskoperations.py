from random import randint
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

def create_disk(parameters, session, **kwargs):
    # Create managed data disk
    task_id = parameters.get('task_id')
    LOG.debug('Create (empty) managed Data Disk:%s' % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "DiskOperation", "create_disk",
                  "started", TASK_STATUS.COMPLETED)
    disk_client = get_gcp_disk_client(parameters)
    op_client = get_gcp_op_client(parameters)
    data_disk_info = parameters.get("data_disk_info")
    if data_disk_info:
        ids = []
        for disk_info in data_disk_info:
            random_num = randint(10000, 99999)
            disk_name = "%s%s" % (disk_info.get('disk_name'), random_num)
            add_audit_log(session, task_id, "DiskOperation", "create_disk:%s" % disk_name,
                          "Started", TASK_STATUS.COMPLETED)
            data = {
                'name': disk_name,
                'size_gb': disk_info.get('disk_size_GB'),
                'type_': "projects/%s/zones/%s/diskTypes/%s" %
                         (parameters.get('gcp_project'),
                          parameters.get('zone'),
                          disk_info.get('disk_type'))
            }
            resource = compute_v1.Disk(data)
            op = disk_client.insert(
                project=parameters.get('gcp_project'),
                zone=parameters.get('zone'),
                disk_resource=resource)
            while op.status != compute_v1.Operation.Status.DONE:
                op = op_client.wait(
                    operation=op.name, zone=parameters.get('zone'),
                    project=parameters.get('gcp_project'))

            add_audit_log(session, task_id, "DiskOperation", "create_disk:%s" % disk_name,
                          "Success", TASK_STATUS.COMPLETED)
            response = disk_client.get(
                project=parameters.get('gcp_project'),
                zone=parameters.get('zone'),
                disk=disk_name)
            LOG.debug('Create Disk response:%s' % response,
                      {'task_id': task_id})
            ids.append(str(response.id))
        if ids:
            tf_obj = TerraformClass(config=kwargs.get('config'), db_conn=session,
                                    task_id=task_id, env_vars=kwargs.get('env_vars'))
            tf_obj(state="add_disk", payload=parameters, resource_ids=ids, index=0)
        add_audit_log(session, task_id, "DiskOperation", "create_disk",
                      "Success", TASK_STATUS.COMPLETED)
    else:
        add_audit_log(session, task_id, "DiskOperation", "create_disk",
                      "No Disk information in the request",
                      TASK_STATUS.COMPLETED)

def delete_disk(parameters, session, **kwargs):
    # Delete managed data disk
    task_id = parameters.get('task_id')
    LOG.debug('Delete (empty) managed Data Disk:%s' % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "DiskOperation", "delete_disk",
                  "started", TASK_STATUS.COMPLETED)
    data_disk_info = parameters.get("data_disk_info")
    disk_client = get_gcp_disk_client(parameters)
    op_client = get_gcp_op_client(parameters)
    disks_attached = []
    disks_deleted = []
    for disk_name in data_disk_info:
        add_audit_log(session, task_id, "DiskOperation", "delete_disk%s" % disk_name,
                      "started", TASK_STATUS.COMPLETED)
        try:
            op = disk_client.delete(
                project=parameters.get('gcp_project'),
                zone=parameters.get('zone'),
                disk=disk_name)
            while op.status != compute_v1.Operation.Status.DONE:
                op = op_client.wait(
                    operation=op.name, zone=parameters.get('zone'),
                    project=parameters.get('gcp_project'))
            disks_deleted.append(disk_name)
        except Exception as ex:
            if "is already being used by" in str(ex):
                disks_attached.append(str(ex))
        add_audit_log(session, task_id, "DiskOperation", "delete_disk%s" % disk_name,
                      "Success", TASK_STATUS.COMPLETED)
    add_audit_log(session, task_id, "DiskOperation", "delete_disk:%s:%s" %
                  (disks_deleted, disks_attached), "Success", TASK_STATUS.COMPLETED)