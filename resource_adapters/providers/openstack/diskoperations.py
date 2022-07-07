from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from resource_adapters.utils.openstack_clients import get_openstack_client
#from pyVmomi import vim

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
    task_id = parameters.get('task_id')
    LOG.debug("Delete disk Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
        
    disks_failed = []
    disk_info = parameters.get('disk_info')
    if isinstance(disk_info, str):
        disk_info = [disk_info]
    for disk_name in disk_info:
        add_audit_log(session, task_id, "DiskOperation", "delete_disk:%s" % disk_name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            disk = client.get_volume(disk_name)
            if disk is None:
                raise Exception('No disk {} found'.format(disk_name))
            client.delete_volume(name_or_id = disk_name,wait = True)
        except Exception as ex:
            add_audit_log(session, task_id, "DiskOperation", "delete_disk:%s" % disk_name,
                        str(ex), TASK_STATUS.FAILED)
            disks_failed.append(disk_name)

        add_audit_log(session, task_id, "DiskOperation", "delete_disk:%s" % disk_name,
                        "Success", TASK_STATUS.COMPLETED)
    if disks_failed:
        add_audit_log(session, task_id, "DiskOperation", "delete_disk",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following disk ops failed {}'.format(disks_failed))

def increase_disk_size(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("increase_disk_size Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    disks_failed = []
    disk_info = parameters.get('disk_info')
    if isinstance(disk_info, str):
        disk_info = [disk_info]
    for data in disk_info:
        disk_name = data.get('disk_name')
        disk_size = data.get('disk_size')
        add_audit_log(session, task_id, "DiskOperation", "increase_disk_size:%s" % disk_name,
                    "started", TASK_STATUS.COMPLETED)
        
        disk = client.get_volume(disk_name)
        if disk is None:
            add_audit_log(session, task_id, "DiskOperation", "increase_disk_size:%s" % disk_name,
                        "No disk {} exists".format(disk_name), TASK_STATUS.FAILED)
            
            disks_failed.append(disk_name)
        if disk_size < disk.size:
            add_audit_log(session, task_id, "DiskOperation", "increase_disk_size:%s" % disk_name,
                        "Disk size smaller than previous value", TASK_STATUS.FAILED)
            
            disks_failed.append(disk_name)
        try:
            client.block_storage.extend_volume(disk.id,disk_size)
        except Exception as ex:
            add_audit_log(session, task_id, "DiskOperation", "increase_disk_size:%s" % disk_name,
                        "Failed", TASK_STATUS.FAILED)
            disks_failed.append(disk_name)

        add_audit_log(session, task_id, "DiskOperation", "increase_disk_size:%s" % disk_name,
                        "Success", TASK_STATUS.COMPLETED)
    if disks_failed:
        add_audit_log(session, task_id, "DiskOperation", "increase_disk_size",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following disk ops failed {}'.format(disks_failed))