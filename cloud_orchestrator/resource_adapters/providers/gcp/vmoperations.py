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

def start_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Start VM:%s" % parameters, {'task_id': task_id})
    vm_list = parameters.get('vm_name')
    instance_client = get_gcp_instance_client(parameters)
    op_client = get_gcp_op_client(parameters)
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "start_vm:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        op = instance_client.start(project=parameters.get('gcp_project'),
                                   zone=parameters.get('zone'),
                                   instance=vm_name)
        while op.status != compute_v1.Operation.Status.DONE:
            op = op_client.wait(
                operation=op.name, zone=parameters.get('zone'),
                project=parameters.get('gcp_project')
            )
        if op.http_error_status_code == 0:
            add_audit_log(session, task_id, "VmOperation", "start_vm:%s" % vm_name,
                          "Success", TASK_STATUS.COMPLETED)
        else:
            add_audit_log(session, task_id, "VmOperation", "start_vm:%s" % vm_name,
                          "{}-{}".format(op.http_error_status_code, op.http_error_message),
                          TASK_STATUS.FAILED)
            raise Exception("Failed to perform operation:%s" % str(op.http_error_message))

def stop_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Stop VM:%s" % parameters, {'task_id': task_id})
    vm_list = parameters.get('vm_name')
    instance_client = get_gcp_instance_client(parameters)
    op_client = get_gcp_op_client(parameters)
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "stop_vm:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        op = instance_client.stop(project=parameters.get('gcp_project'),
                                  zone=parameters.get('zone'),
                                  instance=vm_name)

        while op.status != compute_v1.Operation.Status.DONE:
            op = op_client.wait(
                operation=op.name, zone=parameters.get('zone'),
                project=parameters.get('gcp_project')
            )

        if op.http_error_status_code == 0:
            add_audit_log(session, task_id, "VmOperation", "stop_vm:%s" % vm_name,
                          "Success", TASK_STATUS.COMPLETED)
        else:
            add_audit_log(session, task_id, "VmOperation", "stop_vm:%s" % vm_name,
                          "{}-{}".format(op.http_error_status_code, op.http_error_message),
                          TASK_STATUS.FAILED)
            raise Exception("Failed to perform operation:%s" % str(op.http_error_message))

def delete_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Delete VM:%s" % parameters, {'task_id': task_id})
    vm_list = parameters.get('vm_name')
    instance_client = get_gcp_instance_client(parameters)
    op_client = get_gcp_op_client(parameters)
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "delete_vm:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)

        op = instance_client.delete(project=parameters.get('gcp_project'),
                                    zone=parameters.get('zone'),
                                    instance=vm_name)
        while op.status != compute_v1.Operation.Status.DONE:
            op = op_client.wait(
                operation=op.name, zone=parameters.get('zone'),
                project=parameters.get('gcp_project')
            )

        if op.http_error_status_code == 0:
            add_audit_log(session, task_id, "VmOperation", "delete_vm:%s" % vm_name,
                          "Success", TASK_STATUS.COMPLETED)
        else:
            add_audit_log(session, task_id, "VmOperation", "delete_vm:%s" % vm_name,
                          "{}-{}".format(op.http_error_status_code, op.http_error_message),
                          TASK_STATUS.FAILED)
            raise Exception("Failed to perform operation:%s" % str(op.http_error_message))

def reset_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Reset VM:%s" % parameters, {'task_id': task_id})
    vm_list = parameters.get('vm_name')
    instance_client = get_gcp_instance_client(parameters)
    op_client = get_gcp_op_client(parameters)
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "reset_vm:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)

        op = instance_client.reset(project=parameters.get('gcp_project'),
                                   zone=parameters.get('zone'),
                                   instance=vm_name)

        while op.status != compute_v1.Operation.Status.DONE:
            op = op_client.wait(
                operation=op.name, zone=parameters.get('zone'),
                project=parameters.get('gcp_project')
            )

        if op.http_error_status_code == 0:
            add_audit_log(session, task_id, "VmOperation", "reset_vm:%s" % vm_name,
                          "Success", TASK_STATUS.COMPLETED)
        else:
            add_audit_log(session, task_id, "VmOperation", "reset_vm:%s" % vm_name,
                          "{}-{}".format(op.http_error_status_code, op.http_error_message),
                          TASK_STATUS.FAILED)
            raise Exception("Failed to perform operation:%s" % str(op.http_error_message))

def change_vm_size(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Change VM:%s" % parameters, {'task_id': task_id})
    vm_list = parameters.get('vm_name')
    instance_client = get_gcp_instance_client(parameters)
    op_client = get_gcp_op_client(parameters)
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "change_vm_size:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        # For changing vm size, vm needs to be stopped first
        stop_vm(vm_name, parameters)
        machine_type = compute_v1.InstancesSetMachineTypeRequest()
        machine_type.machine_type = "zones/{}/machineTypes/{}".format(
            parameters.get('zone'), parameters.get('vm_size'))
        try:
            op = instance_client.set_machine_type(
                project=parameters.get('gcp_project'), zone=parameters.get('zone'),
                instance=vm_name,
                instances_set_machine_type_request_resource=machine_type)
            while op.status != compute_v1.Operation.Status.DONE:
                op = op_client.wait(
                    operation=op.name, zone=parameters.get('zone'),
                    project=parameters.get('gcp_project')
                )
            if op.http_error_status_code == 0:
                add_audit_log(session, task_id, "VmOperation", "change_vm_size:%s" % vm_name,
                              "Success", TASK_STATUS.COMPLETED)
            else:
                add_audit_log(session, task_id, "VmOperation", "change_vm_size:%s" % vm_name,
                              "{}-{}".format(op.http_error_status_code, op.http_error_message),
                              TASK_STATUS.FAILED)
                raise Exception("Failed to perform operation:%s" % str(op.http_error_message))
        except Exception as ex:
            raise ex
        finally:
            start_vm(vm_name, parameters)

def add_disk(parameters, session, **kwargs):
    # Create managed data disk
    task_id = parameters.get('task_id')
    LOG.debug("Create (empty) managed Data Disk:%s" % parameters,
              {'task_id': task_id})
    vm_list = parameters.get('vm_name')
    instance_client = get_gcp_instance_client(parameters)
    disk_client = get_gcp_disk_client(parameters)
    op_client = get_gcp_op_client(parameters)
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    data_disk_info = parameters.get("data_disk_info")
    for vm_name in vm_list:
        index = vm_list.index(vm_name)
        add_audit_log(session, task_id, "VmOperation", "add_disk:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        if data_disk_info:
            ids = []
            response = instance_client.get(
                project=parameters.get('gcp_project'),
                zone=parameters.get('zone'),
                instance=vm_name)
            disk_count = len(response.disks)
            print("Disk info is:%s" % response.disks)
            LOG.debug("VM disk info:%s" % response.disks,
                      {'task_id': task_id})
            for num in range(len(data_disk_info)):
                disk_info = data_disk_info[num]
                random_num = randint(10000, 99999)
                disk_name = "%sdatadisk%s%s" % \
                            (vm_name.replace("-", "").replace("_", ""),
                             num, random_num)
                data = {
                    'name': disk_name,
                    'size_gb': int(disk_info.get('disk_size_GB')),
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

                try:
                    response = disk_client.get(
                        project=parameters.get('gcp_project'),
                        zone=parameters.get('zone'),
                        disk=disk_name)
                    LOG.debug('Create Disk response:%s' % response,
                              {'task_id': task_id})
                    add_audit_log(session, task_id, "VmOperation", "add_disk:%s" % disk_name,
                                  "Success", TASK_STATUS.COMPLETED)
                except Exception as ex:
                    add_audit_log(session, task_id, "VmOperation", "add_disk:%s" % disk_name,
                                  "%s" % str(ex), TASK_STATUS.COMPLETED)
                    raise ex
                data = {
                    "disk_size_gb": disk_info.get('disk_size_gb'),
                    "source": "projects/%s/zones/%s/disks/%s" %
                              (parameters.get('gcp_project'),
                               parameters.get('zone'),
                               disk_name),
                    "index": disk_count
                }
                disk = compute_v1.types.AttachedDisk(data)
                op = instance_client.attach_disk(
                    project=parameters.get('gcp_project'),
                    zone=parameters.get('zone'),
                    instance=vm_name,
                    attached_disk_resource=disk)

                while op.status != compute_v1.Operation.Status.DONE:
                    op = op_client.wait(
                        operation=op.name, zone=parameters.get('zone'),
                        project=parameters.get('gcp_project')
                    )
                disk_count += 1
                add_audit_log(session, task_id, "VmOperation", "attach_disk:%s" % disk_name,
                              "Success", TASK_STATUS.COMPLETED)
                response = disk_client.get(
                    project=parameters.get('gcp_project'),
                    zone=parameters.get('zone'),
                    disk=disk_name)
                print(response)
                ids.append(str(response.id))
            if ids:
                tf_obj = TerraformClass(config=kwargs.get('config'), db_conn=session,
                                        task_id=task_id, env_vars=kwargs.get('env_vars'))
                tf_obj(state="add_disk", payload=parameters, resource_ids=ids,
                       index=index)

            add_audit_log(session, task_id, "VmOperation", "add_disk:%s" % vm_name,
                          "Success", TASK_STATUS.COMPLETED)

        else:
            add_audit_log(session, task_id, "VmOperation", "add_disk",
                               "No Disk information in the request",
                               TASK_STATUS.COMPLETED)

def change_disk_size(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Change Disk size:%s" % parameters, {'task_id': task_id})
    vm_list = parameters.get('vm_name')
    instance_client = get_gcp_instance_client(parameters)
    disk_client = get_gcp_disk_client(parameters)
    op_client = get_gcp_op_client(parameters)
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    data_disk_info = parameters.get("data_disk_info")
    LOG.debug("Data disk info:%s" % data_disk_info, {'task_id': task_id})
    for vm_name in vm_list:
        index = vm_list.index(vm_name)
        ids = []
        change_disks = []
        failed_disks = []
        if data_disk_info:
            for disk_info in data_disk_info:
                disk_size = disk_info.get("disk_size_GB")
                disk_name = disk_info.get("disk_name")
                add_audit_log(session, task_id, "VmOperation", "change_disk_size:%s" % disk_name,
                              "started", TASK_STATUS.COMPLETED)
                LOG.debug('Update disk size:%s %s' % (disk_name, disk_size),
                          {'task_id': task_id})
                disk = compute_v1.DisksResizeRequest({"size_gb": disk_size})
                try:
                    op = disk_client.resize(
                        project=parameters.get('gcp_project'),
                        zone=parameters.get('zone'),
                        disk=disk_name, disks_resize_request_resource=disk)
                    while op.status != compute_v1.Operation.Status.DONE:
                        op = op_client.wait(
                            operation=op.name, zone=parameters.get('zone'),
                            project=parameters.get('gcp_project'))
                    add_audit_log(session, task_id, "VmOperation", "change_disk_size:%s" % disk_name,
                                  "Success", TASK_STATUS.COMPLETED)
                    response = instance_client.get(
                        project=parameters.get('gcp_project'),
                        zone=parameters.get('zone'),
                        instance=vm_name)
                    change_disks.append(disk_name)
                    ids.append(str(response.id))
                except Exception as ex:
                    failed_disks.append(disk_name)
                    add_audit_log(session, task_id, "VmOperation", "change_disk_size:%s" % disk_name,
                                  "%s" % str(ex), TASK_STATUS.FAILED)
            add_audit_log(session, task_id, "VmOperation", "changed_disks:%s, failed disks:%s" %
                          (change_disks, failed_disks), "Success", TASK_STATUS.COMPLETED)
            if ids:
                tf_obj = TerraformClass(config=kwargs.get('config'), db_conn=session,
                                        task_id=task_id, env_vars=kwargs.get('env_vars'))
                tf_obj(state="add_disk", payload=parameters, resource_ids=ids,
                       index=index)
        else:
            add_audit_log(session, task_id, "VmOperation", "change_disk_size",
                          "No Disk information in the request",
                          TASK_STATUS.COMPLETED)

def attach_disk(parameters, session, **kwargs):
    # Attach existing data disk
    task_id = parameters.get('task_id')
    LOG.debug("Attach existing disk:%s" % parameters, {'task_id': task_id})
    vm_list = parameters.get('vm_name')
    instance_client = get_gcp_instance_client(parameters)
    disk_client = get_gcp_disk_client(parameters)
    op_client = get_gcp_op_client(parameters)
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    data_disk_info = parameters.get("data_disk_info")
    LOG.debug("Data disk info:%s" % data_disk_info, {'task_id': task_id})
    for vm_name in vm_list:
        index = vm_list.index(vm_name)
        add_audit_log(session, task_id, "VmOperation", "attach_disk:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        already_attached = []
        attached_disks = []
        failed_disks = []
        if data_disk_info:
            ids = []
            response = instance_client.get(
                project=parameters.get('gcp_project'),
                zone=parameters.get('zone'),
                instance=vm_name)
            disk_count = len(response.disks)
            LOG.debug("VM disk info:%s" % response.disks,
                      {'task_id': task_id})
            for disk_info in data_disk_info:
                disk_name = disk_info.get('disk_name')
                try:
                    response = disk_client.get(
                        project=parameters.get('gcp_project'),
                        zone=parameters.get('zone'),
                        disk=disk_name)
                    LOG.debug("Disk info:%s" % response, {'task_id': task_id})
                    if response.users:
                        LOG.debug("Disk %s is already attached" % disk_name,
                                  {'task_id': task_id})
                        already_attached.append("%s:%s" % (disk_name, response.users))
                        continue

                    add_audit_log(session, task_id, "VmOperation", "attach_disk:%s" % disk_name,
                                  "started", TASK_STATUS.COMPLETED)
                    data = {
                        "source": "projects/%s/zones/%s/disks/%s" %
                                  (parameters.get('gcp_project'),
                                   parameters.get('zone'),
                                   disk_name),
                        "index": disk_count
                    }
                    disk = compute_v1.types.AttachedDisk(data)
                    op = instance_client.attach_disk(
                        project=parameters.get('gcp_project'),
                        zone=parameters.get('zone'),
                        instance=vm_name,
                        attached_disk_resource=disk)
                    while op.status != compute_v1.Operation.Status.DONE:
                        op = op_client.wait(
                            operation=op.name, zone=parameters.get('zone'),
                            project=parameters.get('gcp_project')
                        )
                    attached_disks.append(disk_name)
                    disk_count += 1
                    add_audit_log(session, task_id, "VmOperation", "attach_disk:%s" % disk_name,
                                  "Success", TASK_STATUS.COMPLETED)
                    ids.append(str(response.id))
                    add_audit_log(session, task_id, "VmOperation", "attach_disk:%s" % disk_name,
                                  "Success", TASK_STATUS.COMPLETED)
                except Exception as ex:
                    add_audit_log(session, task_id, "VmOperation", "attach_disk:%s" % disk_name,
                                  "%s" % str(ex), TASK_STATUS.FAILED)
                    failed_disks.append(disk_name)
            add_audit_log(session, task_id, "VmOperation", "attached_disk:%s, already attached:%s,"
                          " failed disks:%s" %
                          (attached_disks, already_attached, failed_disks),
                          "Success", TASK_STATUS.COMPLETED)
            if ids:
                tf_obj = TerraformClass(config=kwargs.get('config'), db_conn=session,
                                        task_id=task_id, env_vars=kwargs.get('env_vars'))
                tf_obj(state="add_disk", payload=parameters, resource_ids=ids,
                       index=index)
            add_audit_log(session, task_id, "VmOperation", "attach_disk:%s" % vm_name,
                          "Success", TASK_STATUS.COMPLETED)
        else:
            add_audit_log(session, task_id, "VmOperation", "add_disk",
                          "No Disk information in the request",
                          TASK_STATUS.COMPLETED)

def detach_disk(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Detach disk:%s" % parameters, {'task_id': task_id})
    vm_list = parameters.get('vm_name')
    instance_client = get_gcp_instance_client(parameters)
    op_client = get_gcp_op_client(parameters)
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    data_disk_info = parameters.get("data_disk_info")
    LOG.debug("Data disk info:%s" % data_disk_info, {'task_id': task_id})
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "detach_disk",
                           "started", TASK_STATUS.COMPLETED)
        disk_names = []
        detach_disk_dict = {}
        if data_disk_info:
            for disk_info in data_disk_info:
                disk_names.append(disk_info.get("disk_name"))
            response = instance_client.get(
                project=parameters.get('gcp_project'),
                zone=parameters.get('zone'),
                instance=vm_name)
            for disk in response.disks:
                if not disk.boot:
                    disk_name = disk.source.split("/")[-1]
                    if disk_name in disk_names:
                        detach_disk_dict[disk_name] = disk.device_name
            LOG.debug("Detach disk info:%s" % detach_disk_dict,
                      {'task_id': task_id})

            for name, device in detach_disk_dict.items():
                add_audit_log(session, task_id, "VmOperation", "detach_disk:%s" % name,
                                   "started", TASK_STATUS.COMPLETED)
                op = instance_client.detach_disk(
                    project=parameters.get('gcp_project'),
                    zone=parameters.get('zone'),
                    instance=vm_name,
                    device_name=device)
                while op.status != compute_v1.Operation.Status.DONE:
                    op = op_client.wait(
                        operation=op.name, zone=parameters.get('zone'),
                        project=parameters.get('gcp_project')
                    )
                add_audit_log(session, task_id, "VmOperation", "detach_disk:%s" % name,
                              "Success", TASK_STATUS.COMPLETED)
        add_audit_log(session, task_id, "VmOperation", "detach_disk",
                      "Success", TASK_STATUS.COMPLETED)

def add_ip_to_nic(parameters, session, **kwargs):
    # Associate public ip to nic
    task_id = parameters.get('task_id')
    LOG.debug("Add IP to NIC:%s" % parameters, {'task_id': task_id})
    vm_list = parameters.get('vm_name')
    instance_client = get_gcp_instance_client(parameters)
    op_client = get_gcp_op_client(parameters)
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    try:
        ip_config_info = parameters.get('ip_config_info')
    except Exception as ex:
        raise Exception("Ip configuration is missing:%s" % str(ex))
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "add_ip_to_nic:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        for ip_config in ip_config_info:
            nic_name = ip_config.get('nic_name')
            subnet = ip_config.get('subnet')
            public_ip = ip_config.get('address')
            add_audit_log(session, task_id, "VmOperation", "add_ip_to_nic:%s" % public_ip,
                          "Started", TASK_STATUS.COMPLETED)
            instance_details = instance_client.get(
                project=parameters.get('gcp_project'),
                zone=parameters.get('zone'), instance=vm_name)
            LOG.debug("Instance details:%s" % instance_details, {'task_id': task_id})
            nic_details = None
            for nif in instance_details.network_interfaces:
                if nif.name == nic_name:
                    nic_details = nif
                    break
            LOG.debug("Nic details:%s" % nic_details, {'task_id': task_id})
            if nic_details:
                if nic_details.access_configs:
                    access_config_name = nic_details.access_configs[0].name
                    op = instance_client.delete_access_config(
                        project=parameters.get('gcp_project'),
                        zone=parameters.get('zone'),
                        instance=vm_name,
                        network_interface=nic_name,
                        access_config=access_config_name)
                    while op.status != compute_v1.Operation.Status.DONE:
                        op = op_client.wait(
                            operation=op.name, zone=parameters.get('zone'),
                            project=parameters.get('gcp_project')
                        )
                data = {"network_tier": "PREMIUM",
                        "nat_i_p": public_ip}
                access_config_resource = compute_v1.AccessConfig(data)
                op = instance_client.add_access_config(
                    project=parameters.get('gcp_project'),
                    zone=parameters.get('zone'),
                    instance=vm_name,
                    network_interface=nic_name,
                    access_config_resource=access_config_resource)
                while op.status != compute_v1.Operation.Status.DONE:
                    op = op_client.wait(
                        operation=op.name, zone=parameters.get('zone'),
                        project=parameters.get('gcp_project')
                    )
                add_audit_log(session, task_id, "VmOperation", "add_ip_to_nic:%s" % public_ip,
                              "Success", TASK_STATUS.COMPLETED)
            else:
                add_audit_log(session, task_id, "VmOperation", "add_ip_to_nic:%s" % public_ip,
                              "Nic info is missing", TASK_STATUS.FAILED)

def remove_ip_from_nic(parameters, session, **kwargs):
    # DeAssociate public ip to nic
    task_id = parameters.get('task_id')
    LOG.debug("Add IP to NIC:%s" % parameters, {'task_id': task_id})
    vm_list = parameters.get('vm_name')
    instance_client = get_gcp_instance_client(parameters)
    op_client = get_gcp_op_client(parameters)
    if isinstance(vm_list, str):
        vm_list = [vm_list]
    try:
        ip_config_info = parameters.get('ip_config_info')
    except Exception as ex:
        raise Exception("Ip configuration is missing:%s" % str(ex))
    for vm_name in vm_list:
        add_audit_log(session, task_id, "VmOperation", "remove_ip_from_nic:%s" % vm_name,
                      "started", TASK_STATUS.COMPLETED)
        for ip_config in ip_config_info:
            nic_name = ip_config.get('nic_name')
            public_ip = ip_config.get('ip_name')
            add_audit_log(session, task_id, "VmOperation", "remove_ip_from_nic:%s" % public_ip,
                          "Started", TASK_STATUS.COMPLETED)
            instance_details = instance_client.get(
                project=parameters.get('gcp_project'),
                zone=parameters.get('zone'), instance=vm_name)
            LOG.debug("Instance details:%s" % instance_details, {'task_id': task_id})
            nic_details = None
            for nif in instance_details.network_interfaces:
                if nif.name == nic_name:
                    nic_details = nif
                    break
            LOG.debug("Nic details:%s" % nic_details, {'task_id': task_id})
            if nic_details:
                access_config_name = nic_details.access_configs[0].name
                op = instance_client.delete_access_config(
                    project=parameters.get('gcp_project'),
                    zone=parameters.get('zone'),
                    instance=vm_name,
                    network_interface=nic_name,
                    access_config=access_config_name)
                while op.status != compute_v1.Operation.Status.DONE:
                    op = op_client.wait(
                        operation=op.name, zone=parameters.get('zone'),
                        project=parameters.get('gcp_project')
                    )
                add_audit_log(session, task_id, "VmOperation", "remove_ip_from_nic:%s" % public_ip,
                              "Success", TASK_STATUS.COMPLETED)
            else:
                add_audit_log(session, task_id, "VmOperation", "remove_ip_from_nic:%s" % public_ip,
                              "Nic info is missing", TASK_STATUS.FAILED)