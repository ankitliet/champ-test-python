from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from resource_adapters.utils.openstack_clients import get_openstack_client
import time
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


def start_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("List Openstack VMs:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    vm_list = parameters.get('vm_names')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "start_vm:%s" % vm_name,
                        "started", TASK_STATUS.COMPLETED)
        try:
            server = client.compute.find_server(vm_name)
            if server is None:
                raise Exception('No VM {} found'.format(vm_name))
            server = server.to_dict()
            id = server.get('id')
            server = client.compute.find_server(id)
            server = server.to_dict()
            client.compute.start_server(id)
            flag = True
            while flag:
                server = client.compute.find_server(id)
                server = server.to_dict()
                if server.get('vm_state') == 'active':
                    flag = False

            
        except Exception as ex:
            add_audit_log(session, task_id, "VmOperation", "start_vm:%s" % vm_name,
                      str(ex), TASK_STATUS.FAILED)
            ops_failed.append(vm_name)

        add_audit_log(session, task_id, "VmOperation", "start_vm:%s" % vm_name,
                          "Success", TASK_STATUS.COMPLETED)
        
    if ops_failed:
        add_audit_log(session, task_id, "VmOperation", "start_vm",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))                  
        

def stop_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Openstack VM ops:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    vm_list = parameters.get('vm_names')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "stop_vm:%s" % vm_name,
                        "started", TASK_STATUS.COMPLETED)
        try:
            server = client.compute.find_server(vm_name)
            if server is None:
                raise Exception('No VM {} found'.format(vm_name))
            server = server.to_dict()
            id = server.get('id')
            server = client.compute.find_server(id)
            server = server.to_dict()
            client.compute.stop_server(id)
            flag = True
            while flag:
                server = client.compute.find_server(id)
                server = server.to_dict()
                if server.get('vm_state') == 'stopped':
                    flag = False

        except Exception as ex:
            add_audit_log(session, task_id, "VmOperation", "stop_vm:%s" % vm_name,
                      str(ex), TASK_STATUS.FAILED)
            ops_failed.append(vm_name)

        add_audit_log(session, task_id, "VmOperation", "stop_vm:%s" % vm_name,
                          "Success", TASK_STATUS.COMPLETED)

    if ops_failed:
        add_audit_log(session, task_id, "VmOperation", "stop_vm",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))                  


def detach_disk(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Detach disk Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    disk_info = parameters.get('disk_info')
    
    for disk in disk_info:
        disk_name = disk.get('disk_name')
        vm_name = disk.get('vm_name')
        add_audit_log(session, task_id, "DiskOperation", "detach_disk:{} from vm:{}".format(disk_name,vm_name),
                    "started", TASK_STATUS.COMPLETED)
        try:
            server = client.get_server(vm_name)
            if server is None:
                raise Exception('No vm {} found'.format(vm_name))
            volume = client.get_volume(disk_name)
            if volume is None:
                raise Exception('No disk {} found'.format(disk_name))

            client.detach_volume(dict(server),dict(volume))
        except Exception as ex:
            add_audit_log(session, task_id, "DiskOperation", str(ex),
                      "Failed", TASK_STATUS.FAILED)
            ops_failed.append(disk_name + ' ## ' + vm_name)

        add_audit_log(session, task_id, "DiskOperation","detach_disk:{} from vm:{}".format(disk_name,vm_name),
                      "Success", TASK_STATUS.COMPLETED)
        
    if ops_failed:
        add_audit_log(session, task_id, "DiskOperation", "detach_disk",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def attach_disk(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Attach disk Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    
    disk_info = parameters.get('disk_info')
    ops_failed = []
    for disk in disk_info:
        disk_name = disk.get('disk_name')
        vm_name = disk.get('vm_name')
        add_audit_log(session, task_id, "DiskOperation", "attach_disk:{} to vm:{}".format(disk_name,vm_name),
                    "started", TASK_STATUS.COMPLETED)
        try:
            server = client.get_server(vm_name)
            if server is None:
                raise Exception('No vm {} found'.format(vm_name))
            volume = client.get_volume(disk_name)
            if volume is None:
                raise Exception('No disk {} found'.format(disk_name))

            client.attach_volume(dict(server),dict(volume))
        except Exception as ex:
            add_audit_log(session, task_id, "DiskOperation", "attach_disk:{} to vm:{}".format(disk_name,vm_name),
                      str(ex), TASK_STATUS.FAILED)
            ops_failed.append(disk_name + ' ## ' + vm_name)

        add_audit_log(session, task_id, "DiskOperation","attach_disk:{} to vm:{}".format(disk_name,vm_name),
                      "Success", TASK_STATUS.COMPLETED)

    if ops_failed:
        add_audit_log(session, task_id, "DiskOperation", "attach_disk",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))                  

def delete_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Delete vm Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    vm_list = parameters.get('vm_names')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "delete_vm:%s" % vm_name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            server = client.get_server(vm_name)
            if server is None:
                raise Exception('No VM {} found'.format(vm_name))
            client.delete_server(name_or_id = vm_name,wait = True)
            
        except Exception as ex:
            add_audit_log(session, task_id, "VmOperation", "delete_vm:%s" % vm_name,
                      str(ex), TASK_STATUS.FAILED)
            ops_failed.append(vm_name)

        add_audit_log(session, task_id, "VmOperation", "delete_vm:%s" % vm_name,
                      "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "VmOperation", "delete_vm",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def create_vm_snapshot(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("create_vm_snapshot Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    vm_info = parameters.get('vm_info')
    if isinstance(vm_info, str):
        vm_info = [vm_info]
    for data in vm_info:
        vm_name = data.get('vm_name')
        snapshot_name = data.get('snapshot_name')
        add_audit_log(session, task_id, "DiskOperation", "create_vm_snapshot:%s" % snapshot_name,
                    "started", TASK_STATUS.COMPLETED)
        
        try:
            client.create_image_snapshot(snapshot_name,vm_name)
            snap = client.compute.find_image(snapshot_name)
            val = 0
            snap = client.compute.get_image(snap.id)
            while snap.status != 'ACTIVE':
                if val == 200:
                    break
                snap = client.compute.get_image(snap.id)
                val = val + 1
            
        except Exception as ex:
            add_audit_log(session, task_id, "DiskOperation", "create_vm_snapshot:%s" % snapshot_name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(snapshot_name)

        add_audit_log(session, task_id, "DiskOperation", "create_vm_snapshot:%s" % snapshot_name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "DiskOperation", "create_vm_snapshot",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_vm_snapshot(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_vm_snapshot Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    snapshots = parameters.get('snapshots')
    if isinstance(snapshots, str):
        snapshots = [snapshots]
    for snap in snapshots:
        add_audit_log(session, task_id, "DiskOperation", "delete_vm_snapshot:%s" % snap,
                    "started", TASK_STATUS.COMPLETED)
        
        try:
            snapshot = client.compute.find_image(snap,False)
            client.compute.delete_image(snapshot.id)
        except Exception as ex:
            add_audit_log(session, task_id, "DiskOperation", "delete_vm_snapshot:%s" % snap,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(snap)

        add_audit_log(session, task_id, "DiskOperation", "delete_vm_snapshot:%s" % snap,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "DiskOperation", "delete_vm_snapshot",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))

def restart_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Restart VMs:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    
    vm_list = parameters.get('vm_names')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        try:
            add_audit_log(session, task_id, "VmOperation", "restart_vm:%s" % vm_name,
                        "started", TASK_STATUS.COMPLETED)
            server = client.compute.find_server(vm_name)
            server = server.to_dict()
            id = server.get('id')
            server = client.compute.find_server(id)
            server = server.to_dict()
            client.compute.reboot_server(id,'HARD')
        except Exception as ex:   
            add_audit_log(session, task_id, "VmOperation", "restart_vm:%s" % vm_name,
                        str(ex), TASK_STATUS.FAILED)
            raise Exception("Restart VmOperation failed:%s" % str(ex))

        add_audit_log(session, task_id, "VmOperation", "restart_vm:%s" % vm_name,
                      "Success", TASK_STATUS.COMPLETED)


def add_floating_ip(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("add_floating_ip Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    vm_info = parameters.get('vm_info')
    if isinstance(vm_info, str):
        vm_info = [vm_info]
    for data in vm_info:
        ip_address = data.get('ip_address')
        vm_name = data.get('vm_name')
        add_audit_log(session, task_id, "DiskOperation", "add_floating_ip:%s" % ip_address,
                    "started", TASK_STATUS.COMPLETED)
        try:
            server = client.compute.find_server(vm_name)
            client.compute.add_floating_ip_to_server(server.id,ip_address)
        except Exception as ex:
            add_audit_log(session, task_id, "DiskOperation", "add_floating_ip:%s" % ip_address,
                        "Failed", TASK_STATUS.FAILED)
            ops_failed.append(ip_address)

        add_audit_log(session, task_id, "DiskOperation", "add_floating_ip:%s" % ip_address,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "DiskOperation", "add_floating_ip",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def detach_floating_ip(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("detach_floating_ip Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    vm_info = parameters.get('vm_info')
    if isinstance(vm_info, str):
        vm_info = [vm_info]
    for data in vm_info:
        ip_address = data.get('ip_address')
        vm_name = data.get('vm_name')
        add_audit_log(session, task_id, "DiskOperation", "detach_floating_ip:%s" % ip_address,
                    "started", TASK_STATUS.COMPLETED)
        try:
            server = client.compute.find_server(vm_name)
            client.compute.remove_floating_ip_from_server(server.id,ip_address)
        except Exception as ex:
            add_audit_log(session, task_id, "DiskOperation", "detach_floating_ip:%s" % ip_address,
                        "Failed", TASK_STATUS.FAILED)
            ops_failed.append(ip_address)

        add_audit_log(session, task_id, "DiskOperation", "detach_floating_ip:%s" % ip_address,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "DiskOperation", "detach_floating_ip",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))

def change_vm_size(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("change_vm_size:%s" % parameters, {'task_id': task_id})
    
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    
    ops_failed = []
    vm_list = parameters.get('vm_names')
    flavor_name = parameters.get('flavor_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        
        try:
            add_audit_log(session, task_id, "VmOperation", "change_vm_size:%s" % vm_name,
                        "started", TASK_STATUS.COMPLETED)
            server = client.compute.find_server(vm_name)
            
            flavor = client.compute.find_flavor(flavor_name)
           
            response = client.compute.resize_server(server.id, flavor.id)
            
            if response is None:
                time.sleep(30)
                client.compute.confirm_server_resize(server.id)
           
        except Exception as ex:
            
            add_audit_log(session, task_id, "VmOperation", "change_vm_size:%s" % vm_name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(vm_name)

        add_audit_log(session, task_id, "VmOperation", "change_vm_size:%s" % vm_name,
                      "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "DiskOperation", "detach_floating_ip",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))

def associate_subnet_to_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("associate_subnet_to_vm Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    subnet_info = parameters.get('subnet_info')
    if isinstance(subnet_info, str):
        subnet_info = [subnet_info]
    for data in subnet_info:
        name = data.get('subnet_name')
        vm_name = data.get('vm_name')
        add_audit_log(session, task_id, "VmOperation", "associate_subnet_to_vm:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            server = client.get_server(vm_name)
            if server is None:
                raise Exception('Server with name {} does not exist'.format(vm_name))
            subnet = client.get_subnet(name)
            if subnet is None:
                raise Exception('Subnet {} does not exist'.format(name))
            subnet_details = {
                'subnet_id': subnet.id,
                'net_id': subnet.network_id
            }
            client.compute.create_server_interface(server.id, **subnet_details)
            add_audit_log(session, task_id, "VmOperation", "associate_subnet_to_vm:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            add_audit_log(session, task_id, "VmOperation", "associate_subnet_to_vm:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

    if ops_failed:
        add_audit_log(session, task_id, "VmOperation", "associate_subnet_to_vm",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))

def associate_security_group_to_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("associate_security_group_to_vm Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    info = parameters.get('info')
    if isinstance(info, str):
        info = [info]
    for data in info:
        security_group_name = data.get('security_group_name')
        vm_name = data.get('vm_name')
        add_audit_log(session, task_id, "VmOperation", "associate_security_group_to_vm:%s" %
                      security_group_name,
                      "started", TASK_STATUS.COMPLETED)
        try:
            server = client.get_server(vm_name)
            if server is None:
                raise Exception('Server with name {} does not exist'.format(vm_name))
            security_group_details = client.get_security_group(security_group_name)
            if security_group_details is None:
                raise Exception('Subnet {} does not exist'.format(security_group_name))
            #add security group to vm    
            client.compute.add_security_group_to_server(server=server.id, security_group=security_group_details)
            add_audit_log(session, task_id, "VmOperation", "associate_security_group_to_vm:%s" %
                          security_group_name, "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            add_audit_log(session, task_id, "VmOperation", "associate_security_group_to_vm:%s" %
                          security_group_name, str(ex), TASK_STATUS.FAILED)
            ops_failed.append(security_group_name)

    if ops_failed:
        add_audit_log(session, task_id, "VmOperation", "associate_security_group_to_vm",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))
        
def remove_security_group_from_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("remove_security_group_from_vm Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    info = parameters.get('info')
    if isinstance(info, str):
        info = [info]
    for data in info:
        security_group_name = data.get('security_group_name')
        vm_name = data.get('vm_name')
        add_audit_log(session, task_id, "VmOperation", "remove_security_group_from_vm:%s" % security_group_name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            server = client.get_server(vm_name)
            if server is None:
                raise Exception('Server with name {} does not exist'.format(vm_name))
            security_group_details = client.get_security_group(security_group_name)
            if security_group_details is None:
                raise Exception('Security Group {} does not exist'.format(name))
            
            #remove security group to vm    
            client.compute.remove_security_group_from_server(server=server.id,
                                                             security_group=security_group_details)
            add_audit_log(session, task_id, "VmOperation", "remove_security_group_from_vm:%s"
                          % security_group_name,
                          "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            add_audit_log(session, task_id, "VmOperation", "remove_security_group_from_vm:%s" %
                          security_group_name,
                          str(ex), TASK_STATUS.FAILED)
            ops_failed.append(security_group_name)

    if ops_failed:
        add_audit_log(session, task_id, "VmOperation", "remove_security_group_from_vm",
                      "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))