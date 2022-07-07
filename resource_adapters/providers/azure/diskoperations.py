from random import randint
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from azure.mgmt.compute.models import DiskCreateOption
from util.core.app.terraform_resource import TerraformClass
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

def delete_disk(parameters, session, **kwargs):
    # Create managed data disk
    task_id = parameters.get('task_id')
    compute_client = get_compute_client(parameters)
    LOG.debug("Delete disk:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "DiskOperation", "delete_disk",
                  "started", TASK_STATUS.COMPLETED)
    data_disk_info = parameters.get("data_disk_info")
    delete_disk_handle = []
    attached_disks = []
    attached_disks_by = []
    deleted_disks = []
    for disk_name in data_disk_info:
        disk_obj = compute_client.disks.get(parameters.get('resource_group_name'),
                                            disk_name)
        if disk_obj.disk_state.lower() == "attached":
            attached_disks.append(disk_name)
            attached_disks_by.append(disk_obj.managed_by)
            continue
        add_audit_log(session, task_id, "DiskOperation", "delete_disk",
                      "started:%s" % disk_name, TASK_STATUS.COMPLETED)
        async_delete_disk = compute_client.disks.begin_delete(
            parameters.get('resource_group_name'), disk_name)
        deleted_disks.append(disk_name)
        delete_disk_handle.append(async_delete_disk)
    for async_delete_disk in delete_disk_handle:
        async_delete_disk.wait()
    add_audit_log(session, task_id, "DiskOperation", "delete_disk",
                  "Success", TASK_STATUS.COMPLETED)
    if attached_disks:
        raise Exception("Deleted disks are: %s, Disks %s are attached to:%s" %
                        (deleted_disks, attached_disks, attached_disks_by))

def create_disk(parameters, session, **kwargs):
    # Create managed data disk
    task_id = parameters.get('task_id')
    compute_client = get_compute_client(parameters)
    LOG.debug("Create (empty) managed Data Disk:%s" % parameters,
              {'task_id': task_id})
    data_disk_info = parameters.get("data_disk_info")
    if data_disk_info:
        ids = []
        for num in range(len(data_disk_info)):
            disk_info = data_disk_info[num]
            random_num = randint(10000, 99999)
            disk_name = "%s_%s" % (disk_info.get('disk_name'), random_num)
            add_audit_log(session, task_id, "DiskOperation", "create_disk:%s" % disk_name,
                          "Started", TASK_STATUS.COMPLETED)
            async_disk_creation = compute_client.disks.begin_create_or_update(
                parameters.get('resource_group_name'),
                disk_name,
                {
                    'location': parameters.get("location"),
                    'disk_size_gb': disk_info.get('disk_size_GB'),
                    'sku': {"name": disk_info.get('sku'),
                            "tier": disk_info.get('tier', "P1")},
                    'creation_data': {
                        'create_option': DiskCreateOption.empty
                    }
                }
            )
            async_disk_creation.wait()
            data_disk = async_disk_creation.result()
            LOG.debug("Data disk:%s" % data_disk, {'task_id': task_id})
            add_audit_log(session, task_id, "DiskOperation", "create_disk:%s" % disk_name,
                          "Success", TASK_STATUS.COMPLETED)
        if ids:
            tf_obj = TerraformClass(config=kwargs.get('config'), db_conn=session,
                                    task_id=task_id, env_vars=kwargs.get('env_vars'))
            tf_obj(state="add_disk", payload=parameters, resource_ids=ids,
                   index=0)
    else:
        add_audit_log(session, task_id, "DiskOperation", "create_disk",
                      "No Disk information in the request", TASK_STATUS.COMPLETED)