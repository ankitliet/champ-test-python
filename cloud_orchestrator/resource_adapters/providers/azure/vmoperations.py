
from random import randint
from azure.mgmt.compute.models import DiskCreateOption
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
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

def start_vm(parameters, session, **kwargs):
    # Start the VM
    task_id = parameters.get('task_id')
    LOG.debug("Start VM:%s" % parameters, {'task_id': task_id})
    compute_client = get_compute_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "start_vm:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        async_vm_start = compute_client.virtual_machines.begin_start(
            parameters.get('resource_group_name'), vm_name)
        async_vm_start.wait()
        add_audit_log(session, task_id, "VmOperation", "start_vm:%s" % vm_name,
                      "Success", TASK_STATUS.COMPLETED)

def stop_vm(parameters, session, **kwargs):
    # Stop the VM
    task_id = parameters.get('task_id')
    LOG.debug("Stop VM:%s" % parameters, {'task_id': task_id})
    compute_client = get_compute_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "stop_vm:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        async_vm_stop = compute_client.virtual_machines.begin_power_off(
            parameters.get('resource_group_name'), vm_name)
        async_vm_stop.wait()
        add_audit_log(session, task_id, "VmOperation", "stop_vm:%s" % vm_name,
                      "Success", TASK_STATUS.COMPLETED)

def restart_vm(parameters, session, **kwargs):
    # restart the VM
    task_id = parameters.get('task_id')
    LOG.debug("Restart VM:%s" % parameters, {'task_id': task_id})
    compute_client = get_compute_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "restart_vm:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        async_vm_stop = compute_client.virtual_machines.begin_restart(
            parameters.get('resource_group_name'), vm_name)
        async_vm_stop.wait()
        add_audit_log(session, task_id, "VmOperation", "restart_vm:%s" % vm_name,
                      "Success", TASK_STATUS.COMPLETED)

def delete_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Delete VM:%s" % parameters, {'task_id': task_id})
    compute_client = get_compute_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "delete_vm:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        async_vm_delete = compute_client.virtual_machines.begin_delete(
            parameters.get('resource_group_name'), vm_name)
        async_vm_delete.wait()
        add_audit_log(session, task_id, "VmOperation", "delete_vm:%s" % vm_name,
                      "Success", TASK_STATUS.COMPLETED)

def add_disk(parameters, session, **kwargs):
    # Create managed data disk
    task_id = parameters.get('task_id')
    LOG.debug("Add disk:%s" % parameters, {'task_id': task_id})
    compute_client = get_compute_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    data_disk_info = parameters.get("data_disk_info")
    for vm_name in vm_list:
        index = vm_list.index(vm_name)
        add_audit_log(session, task_id, "VmOperation", "add_disk:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        if data_disk_info:
            # Get the virtual machine by name
            virtual_machine = compute_client.virtual_machines.get(
                parameters.get('resource_group_name'), vm_name)
            LOG.debug("Storage profile:%s" % virtual_machine.storage_profile,
                      {'task_id': task_id})
            num_disks = len(virtual_machine.storage_profile.data_disks)
            # Add os type disk
            num_disks += 1
            location = virtual_machine.location
            ids = []
            for num in range(len(data_disk_info)):
                disk_info = data_disk_info[num]
                random_num = randint(10000, 99999)
                disk_name = "%s_data_disk_%s_%s" % (vm_name, num, random_num)
                async_disk_creation = compute_client.disks.begin_create_or_update(
                    parameters.get('resource_group_name'),
                    disk_name,
                    {
                        'location': location,
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
                add_audit_log(session, task_id, "VmOperation", "add_disk:%s" % disk_name,
                              "Success", TASK_STATUS.COMPLETED)

                # Attach data disk
                ids.append(data_disk.id)
                virtual_machine.storage_profile.data_disks.append({
                    'lun': num_disks,
                    'name': disk_name,
                    'create_option': DiskCreateOption.attach,
                    'managed_disk': {
                        'id': data_disk.id
                    }
                })
                async_disk_attach = \
                    compute_client.virtual_machines.begin_create_or_update(
                    parameters.get('resource_group_name'),
                    virtual_machine.name, virtual_machine)
                async_disk_attach.wait()
                add_audit_log(session, task_id, "VmOperation", "attach_disk:%s" % disk_name,
                              "Success", TASK_STATUS.COMPLETED)
                num_disks += 1
            if ids:
                tf_obj = TerraformClass(config=kwargs.get('config'), db_conn=session,
                                        task_id=task_id, env_vars=kwargs.get('env_vars'))
                tf_obj(state="add_disk", payload=parameters, resource_ids=ids,
                       index=index)
        else:
            add_audit_log(session, task_id, "VmOperation", "add_disk",
                          "No Disk information in the request", TASK_STATUS.COMPLETED)

def attach_disk(parameters, session, **kwargs):
    # Attach existing data disk
    task_id = parameters.get('task_id')
    LOG.debug("Attach existing disk to vm:%s" % parameters, {'task_id': task_id})
    compute_client = get_compute_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    data_disk_info = parameters.get('data_disk_info')
    for vm_name in vm_list:
        index = vm_list.index(vm_name)
        already_attached = []
        attached_disks = []
        failed_disks = []
        if data_disk_info:
            # Get the virtual machine by name
            virtual_machine = compute_client.virtual_machines.get(
                parameters.get('resource_group_name'), vm_name)
            LOG.debug("Storage profile:%s" % virtual_machine.storage_profile.data_disks,
                      {'task_id': task_id})
            num_disks = len(virtual_machine.storage_profile.data_disks)
            # Add os type disk
            num_disks += 1
            ids = []
            for disk_info in data_disk_info:
                disk_name = disk_info.get('disk_name')
                try:
                    disk_obj = compute_client.disks.get(
                        parameters.get('resource_group_name'), disk_name)
                    LOG.debug("Disk details are::%s" % disk_obj)
                    if disk_obj.disk_state.lower() == "attached":
                        LOG.debug("Disk %s is already attached:%s" % (disk_name, disk_obj),
                                  {'task_id': task_id})
                        already_attached.append(disk_name)
                        continue
                    # Attach data disk
                    add_audit_log(session, task_id, "VmOperation",
                                  "attach_disk:%s" % disk_name,
                                  "started", TASK_STATUS.COMPLETED)
                    virtual_machine.storage_profile.data_disks.append({
                        'lun': num_disks,
                        'name': disk_name,
                        'create_option': DiskCreateOption.attach,
                        'managed_disk': {
                            'id': disk_obj.id
                        }
                    })
                    async_disk_attach = \
                        compute_client.virtual_machines.begin_create_or_update(
                            parameters.get('resource_group_name'),
                            virtual_machine.name, virtual_machine)
                    async_disk_attach.wait()
                    add_audit_log(session, task_id, "VmOperation",
                                  "attach_disk:%s" % disk_name,
                                  "Success", TASK_STATUS.COMPLETED)
                    attached_disks.append(disk_name)
                    ids.append(disk_obj.id)
                    num_disks += 1
                except Exception as ex:
                    add_audit_log(session, task_id, "VmOperation",
                                  "attach_disk:%s" % disk_name,
                                  "%s" % str(ex), TASK_STATUS.FAILED)
                    failed_disks.append(disk_name)

            add_audit_log(session, task_id, "VmOperation", "attached_disk:%s, already attached:%s,"
                          " failed disks:%s" % (attached_disks, already_attached, failed_disks),
                          "Success", TASK_STATUS.COMPLETED)
            if ids:
                tf_obj = TerraformClass(config=kwargs.get('config'), db_conn=session,
                                        task_id=task_id, env_vars=kwargs.get('env_vars'))
                tf_obj(state="add_disk", payload=parameters, resource_ids=ids,
                       index=index)
        else:
            add_audit_log(session, task_id, "VmOperation", "attach_disk",
                          "No Disk information in the request", TASK_STATUS.COMPLETED)

def change_disk_size(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Change disk size for Data Disk:%s" % parameters, {'task_id': task_id})
    compute_client = get_compute_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    data_disk_info = parameters.get('data_disk_info')
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "change_disk_size:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        # Deallocating the VM (in preparation for a disk resize)
        LOG.debug("Deallocating the VM to prepare for a disk resize",
                  {'task_id': task_id})
        async_vm_deallocate = compute_client.virtual_machines.begin_deallocate(
            parameters.get('resource_group_name'), vm_name)
        async_vm_deallocate.wait()

        # Increase disk size
        LOG.debug("Data disk info:%s" % data_disk_info, {'task_id': task_id})
        for disk_info in data_disk_info:
            disk_size = disk_info.get("disk_size_GB")
            disk_name = disk_info.get("disk_name")
            LOG.debug('Update OS disk size', {'task_id': task_id})
            disk_obj = compute_client.disks.get(parameters.get('resource_group_name'),
                                                disk_name)
            disk_obj.disk_size_gb = disk_size
            async_disk_update = compute_client.disks.begin_create_or_update(
                parameters.get('resource_group_name'),
                disk_name, disk_obj
            )
            async_disk_update.wait()
            add_audit_log(session, task_id, "VmOperation", "change_disk_size:%s" % disk_name,
                          "Success", TASK_STATUS.COMPLETED)

def detach_disk(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Detach Disk:%s" % parameters, {'task_id': task_id})
    compute_client = get_compute_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    data_disk_info = parameters.get('data_disk_info')
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "detach_disk:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        disk_names = []
        for disk_info in data_disk_info:
            disk_names.append(disk_info.get('disk_name'))
        virtual_machine = compute_client.virtual_machines.get(
            parameters.get('resource_group_name'), vm_name)
        data_disks = virtual_machine.storage_profile.data_disks
        data_disks[:] = [
            disk for disk in data_disks if disk.name not in disk_names]
        async_vm_update = compute_client.virtual_machines.begin_create_or_update(
            parameters.get('resource_group_name'), vm_name,
            virtual_machine
        )
        async_vm_update.result()
        add_audit_log(session, task_id, "VmOperation", "detach_disk",
                      "Success", TASK_STATUS.COMPLETED)

def change_vm_size(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Change vm size:%s" % parameters, {'task_id': task_id})
    compute_client = get_compute_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "change_vm_size",
                      "started", TASK_STATUS.COMPLETED)
        virtual_machine = compute_client.virtual_machines.get(
            parameters.get('resource_group_name'), vm_name)

        payload = {
                        "location": virtual_machine.location,
                        "hardware_profile": {
                            "vm_size": parameters.get("vm_size")
                        }
                    }
        async_vm_update = \
            compute_client.virtual_machines.begin_create_or_update(
            parameters.get('resource_group_name'), vm_name, payload)
        async_vm_update.wait()
        add_audit_log(session, task_id, "VmOperation", "change_vm_size",
                      "Success", TASK_STATUS.COMPLETED)

def add_ip_to_nic(parameters, session, **kwargs):
    # Associate public ip to nic
    task_id = parameters.get('task_id')
    LOG.debug("Add IP to Nic:%s" % parameters, {'task_id': task_id})
    network_client = get_network_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    try:
        ip_config_info = parameters.get('ip_config_info')
    except Exception as ex:
        raise Exception("Ip configuration is missing:%s" % str(ex))

    ips_added = []
    ips_failed = []
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "add_ip_to_nic:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        for ip_config in ip_config_info:
            nic_name = ip_config.get('nic_name')
            subnet = ip_config.get('subnet')
            public_ip_name = ip_config.get('ip_name')

            subnet_info = network_client.subnets.get(
                parameters.get('resource_group_name'),
                subnet.split("/")[0],
                subnet.split("/")[1])
            LOG.debug("Subnet info is:%s" % subnet_info, {'task_id': task_id})

            ip_info = network_client.public_ip_addresses.get(
                parameters.get('resource_group_name'), public_ip_name)
            LOG.debug("IP info is:%s" % ip_info, {'task_id': task_id})
            add_audit_log(session, task_id, "VmOperation", "add_ip_to_nic:%s" % public_ip_name,
                          "started", TASK_STATUS.COMPLETED)
            try:
                nic_info = network_client.network_interfaces.get(
                    parameters.get('resource_group_name'),
                    network_interface_name=nic_name)

                LOG.debug("Nic info is:%s" % nic_info, {'task_id': task_id})
                ip_configurations = nic_info.ip_configurations
                data = {
                            "name": public_ip_name,
                            "subnet": {"id": subnet_info.id},
                            "public_ip_address": {
                                "id": ip_info.id}
                        }
                ip_configurations.append(data)
                LOG.debug("IP configuration is:%s" % ip_configurations,
                          {'task_id': task_id})
                async_vm_update = network_client.network_interfaces.begin_create_or_update(
                    parameters.get('resource_group_name'),
                    nic_name,
                    {
                        "location": parameters.get('location'),
                        "ip_configurations": ip_configurations
                    })
                async_vm_update.wait()
                ips_added.append(public_ip_name)
                add_audit_log(session, task_id, "VmOperation",
                              "add_ip_to_nic:%s" % public_ip_name,
                              "Success", TASK_STATUS.COMPLETED)
            except Exception as ex:
                ips_failed.append(public_ip_name)
                add_audit_log(session, task_id, "VmOperation",
                              "add_ip_to_nic:%s" % public_ip_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "VmOperation",
                      "add_ip_to_nic Ips added:%s, Ips failed:%s" %
                      (ips_added, ips_failed), "Success", TASK_STATUS.COMPLETED)
    if ips_failed:
        add_audit_log(session, task_id, "VmOperation", "add_ip_to_nic",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ips_failed))

def remove_ip_from_nic(parameters, session, **kwargs):
    # DeAssociate public ip to nic
    task_id = parameters.get('task_id')
    LOG.debug("Remove IP from Nic:%s" % parameters, {'task_id': task_id})
    network_client = get_network_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    try:
        ip_config_info = parameters.get('ip_config_info')
    except Exception as ex:
        raise Exception("Ip configuration is missing:%s" % str(ex))

    ips_added = []
    ips_failed = []
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "remove_ip_from_nic:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        for ip_config in ip_config_info:
            nic_name = ip_config.get('nic_name')
            subnet = ip_config.get('subnet')
            public_ip_name = ip_config.get('ip_name')
            subnet_info = network_client.subnets.get(
                parameters.get('resource_group_name'),
                subnet.split("/")[0], subnet.split("/")[1])
            LOG.debug("Subnet info is:%s" % subnet_info, {'task_id': task_id})

            ip_info = network_client.public_ip_addresses.get(
                parameters.get('resource_group_name'), public_ip_name)
            LOG.debug("IP info is:%s" % ip_info, {'task_id': task_id})
            add_audit_log(session, task_id, "VmOperation",
                          "remove_ip_from_nic:%s" % public_ip_name,
                          "started", TASK_STATUS.COMPLETED)
            try:
                nic_info = network_client.network_interfaces.get(
                    parameters.get('resource_group_name'),
                    network_interface_name=nic_name)

                LOG.debug("Nic info is:%s" % nic_info, {'task_id': task_id})
                ip_configurations = nic_info.ip_configurations
                new_ip_config = []
                for ip_config in ip_configurations:
                    if ip_config.name == public_ip_name:
                        continue
                    new_ip_config.append(ip_config)
                async_vm_update = network_client.network_interfaces.begin_create_or_update(
                    parameters.get('resource_group_name'),
                    nic_name,
                    {
                        "location": parameters.get('location'),
                        "ip_configurations": new_ip_config
                    })
                async_vm_update.wait()
                ips_added.append(public_ip_name)
                add_audit_log(session, task_id, "VmOperation",
                              "remove_ip_from_nic:%s" % public_ip_name,
                              "Success", TASK_STATUS.COMPLETED)
            except Exception as ex:
                ips_failed.append(public_ip_name)
                add_audit_log(session, task_id, "VmOperation",
                              "remove_ip_from_nic:%s" % public_ip_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "VmOperation",
                      "remove_ip_from_nic Ips deleted:%s, Ips failed:%s" %
                      (ips_added, ips_failed), "Success", TASK_STATUS.COMPLETED)
    if ips_failed:
        add_audit_log(session, task_id, "VmOperation", "remove_ip_from_nic",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ips_failed))

def reset_admin_password(parameters, session, **kwargs):
    # Reset Admin passwork
    task_id = parameters.get('task_id')
    LOG.debug("Reset admin password:%s" % parameters, {'task_id': task_id})
    compute_client = get_compute_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]

    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation",
                      "reset_admin_password:%s" % vm_name,
                      "Started", TASK_STATUS.COMPLETED)
        virtual_machine = compute_client.virtual_machines.get(
            parameters.get('resource_group_name'), vm_name)
        LOG.debug("OS profile:%s" % virtual_machine.os_profile,
                  {'task_id': task_id})
        virtual_machine.os_profile.admin_password = parameters.get('new_admin_password')
        async_disk_attach = \
            compute_client.virtual_machines.begin_create_or_update(
                parameters.get('resource_group_name'),
                virtual_machine.name, virtual_machine)
        async_disk_attach.wait()
        add_audit_log(session, task_id, "VmOperation",
                      "reset_admin_password:%s" % vm_name,
                      "Success", TASK_STATUS.COMPLETED)

def add_nic_to_vm(parameters, session, **kwargs):
    # Associate NIC to VM
    task_id = parameters.get('task_id')
    LOG.debug("Add Nic to VM:%s" % parameters, {'task_id': task_id})
    compute_client = get_compute_client(parameters)
    network_client = get_network_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    try:
        nic_info = parameters.get('nic_info')
    except Exception as ex:
        raise Exception("Ip configuration is missing:%s" % str(ex))
    ips_added = []
    ips_failed = []
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation",
                      "add_nic_to_vm:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        virtual_machine = compute_client.virtual_machines.get(
            parameters.get('resource_group_name'), vm_name)
        if virtual_machine.network_profile.network_interfaces:
            network_interfaces = virtual_machine.network_profile.network_interfaces
        else:
            network_interfaces = []
        is_primary = False
        for nics in network_interfaces:
            LOG.debug("NIC:%s" % nics, {'task_id': task_id})
            if not is_primary:
                is_primary = nics.primary

        for nic_name in nic_info:
            LOG.debug("Nic name is:%s" % nic_name, {'task_id': task_id})
            add_audit_log(session, task_id, "VmOperation",
                          "add_nic_to_vm:%s" % nic_name,
                          "started", TASK_STATUS.COMPLETED)
            try:
                nic_info = network_client.network_interfaces.get(
                    parameters.get('resource_group_name'),
                    network_interface_name=nic_name)

                # Deallocating the VM
                LOG.debug("Deallocating the VM to prepare for adding nic",
                          {'task_id': task_id})
                async_vm_deallocate = compute_client.virtual_machines.begin_deallocate(
                    parameters.get('resource_group_name'), vm_name)
                async_vm_deallocate.wait()

                LOG.debug("Nic info is:%s" % nic_info, {'task_id': task_id})
                data = {
                    'id': nic_info.id,
                    'primary': not is_primary
                }
                network_interfaces.append(data)
                virtual_machine.network_profile.network_interfaces = network_interfaces
                async_nic_attach = \
                    compute_client.virtual_machines.begin_create_or_update(
                    parameters.get('resource_group_name'),
                    virtual_machine.name, virtual_machine)
                async_nic_attach.wait()
                ips_added.append(nic_name)
                add_audit_log(session, task_id, "VmOperation",
                              "add_nic_to_vm:%s" % nic_name,
                              "Success", TASK_STATUS.COMPLETED)
            except Exception as ex:
                ips_failed.append(nic_name)
                add_audit_log(session, task_id, "VmOperation",
                              "add_nic_to_vm:%s" % nic_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "VmOperation",
                      "add_nic_to_vm NIC added:%s, NIC failed:%s" %
                      (ips_added, ips_failed), "Success", TASK_STATUS.COMPLETED)
    if ips_failed:
        add_audit_log(session, task_id, "VmOperation", "add_nic_to_vm",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ips_failed))

def remove_nic_from_vm(parameters, session, **kwargs):
    # DeAssociate NIC from VM
    task_id = parameters.get('task_id')
    LOG.debug("Remove Nic from VM:%s" % parameters, {'task_id': task_id})
    compute_client = get_compute_client(parameters)
    vm_list = parameters.get('vm_name')
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    try:
        nic_info = parameters.get('nic_info')
    except Exception as ex:
        raise Exception("Ip configuration is missing:%s" % str(ex))

    for vm_name in vm_list:
        virtual_machine = compute_client.virtual_machines.get(
            parameters.get('resource_group_name'), vm_name)
        network_interfaces = []
        if virtual_machine.network_profile.network_interfaces:
            for nic in virtual_machine.network_profile.network_interfaces:
                if nic.id.split("/")[-1] in nic_info:
                    continue
                network_interfaces.append(nic)

        add_audit_log(session, task_id, "VmOperation",
                      "remove_nic_from_vm:%s" % nic_info,
                      "started", TASK_STATUS.COMPLETED)
        try:
            # Deallocating the VM
            LOG.debug("Deallocating the VM to prepare for adding nic",
                      {'task_id': task_id})
            async_vm_deallocate = compute_client.virtual_machines.begin_deallocate(
                parameters.get('resource_group_name'), vm_name)
            async_vm_deallocate.wait()
            virtual_machine.network_profile.network_interfaces = network_interfaces
            async_nic_dettach = \
                compute_client.virtual_machines.begin_create_or_update(
                    parameters.get('resource_group_name'),
                    virtual_machine.name, virtual_machine)
            async_nic_dettach.wait()
            add_audit_log(session, task_id, "VmOperation",
                          "remove_nic_from_vm:%s" % nic_info,
                          "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            add_audit_log(session, task_id, "VmOperation",
                          "remove_nic_from_vm:%s" % nic_info,
                          "%s" % str(ex), TASK_STATUS.FAILED)
            raise Exception('remove_nic_from_vm ops failed:%s' % str(ex))
        finally:
            start_vm(vm_name, parameters)
        add_audit_log(session, task_id, "VmOperation", "remove_nic_from_vm",
                      "Success", TASK_STATUS.COMPLETED)

def deprovision_vm_scale_set(parameters, session, **kwargs):   
    # Deletes the Virtual Machine Scale Set
    task_id = parameters.get('task_id')
    LOG.debug("Deprovision virtual machine scale set:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "VmOperation", "deprovision_vm_scale_set", 
                  "started", TASK_STATUS.COMPLETED)
    resource_group_name = parameters.get("resource_group_name")
    vmss_list = parameters.get("vm_scale_set")
    compute_client = get_compute_client(parameters)
    try:
        for vmss in vmss_list:
            add_audit_log(session, task_id, "VmOperation", 
                          "deprovision_vm_scale_set:%s" % vmss,
                          "started", TASK_STATUS.COMPLETED)
            compute_client.virtual_machine_scale_sets.begin_delete(resource_group_name, vmss)
            add_audit_log(session, task_id, "VmOperation", 
                               "deprovision_vm_scale_set:%s" % vmss,
                               "Success", TASK_STATUS.COMPLETED)
    except Exception as ex:
        add_audit_log(session, task_id, "VmOperation",
                      "deprovision_vm_scale_set",
                      "%s" % str(ex), TASK_STATUS.FAILED)
        raise Exception("Failed to deprovision virtual machine scale set : %s" % str(ex))   