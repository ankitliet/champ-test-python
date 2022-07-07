from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from resource_adapters.utils.vmware_clients import get_vmware_client
import resource_adapters.providers.vmware.commonoperations as vmware_commonoperations
from pyVmomi import vim
from pyVmomi import pbm, VmomiSupport, SoapStubAdapter
import re, ssl
from random import randint
from util.core.app.terraform_resource import TerraformClass

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
    # Start VM operation
    task_id = parameters.get('task_id')
    LOG.debug(f"Start VMware VM:{parameters}", {'task_id': task_id})
    operation_vm_list = parameters.get('vm_names')
    add_audit_log(session, task_id, "VMOperation",
                  f"start_vm:{operation_vm_list}", "Started", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    all_vm_obj = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True)
    all_vm_list = all_vm_obj.view
    all_vm_obj.Destroy()

    exception_list = []
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]
    for current_vm in all_vm_list:
        if current_vm.name in operation_vm_list:
            add_audit_log(session, task_id, "VMOperation",
                          f"start_vm:{current_vm.name}", "Start", TASK_STATUS.COMPLETED)
            try:
                if current_vm.runtime.powerState == 'poweredOff':
                    TASK = current_vm.PowerOn()
                    vmware_commonoperations.async_tasks_wait(
                        compute_client, [TASK])
                add_audit_log(session, task_id, "VMOperation",
                              f"start_vm:{current_vm.name}", "Success", TASK_STATUS.COMPLETED)
            except Exception as ex:
                add_audit_log(session, task_id, "VMOperation",
                              f"start_vm:{current_vm.name}", f"Failed With Error: {str(ex)}",
                              TASK_STATUS.FAILED)
                exception_list.append({current_vm.name: str(ex)})
            operation_vm_list.remove(current_vm.name)

    if len(operation_vm_list) > 0:
        add_audit_log(session, task_id, "VMOperation", f"start_vm:{operation_vm_list}",
                      "Failed With Error: no such vm available on requested server",
                      TASK_STATUS.FAILED)

    if exception_list:
        add_audit_log(session, task_id, "VMOperation",
                      f"start_vm", f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(f"Failed To Start VMware VM:{exception_list}")


def stop_vm(parameters, session, **kwargs):
    # Stop VM operation
    task_id = parameters.get('task_id')
    LOG.debug(f"Stop VMware VM:{parameters}", {'task_id': task_id})
    operation_vm_list = parameters.get('vm_names')
    add_audit_log(session, task_id, "VMOperation",
                  f"stop_vm:{operation_vm_list}", "Started", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    all_vm_obj = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True)
    all_vm_list = all_vm_obj.view
    all_vm_obj.Destroy()

    exception_list = []
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]
    for current_vm in all_vm_list:
        if current_vm.name in operation_vm_list:
            add_audit_log(session, task_id, "VMOperation",
                          f"stop_vm:{current_vm.name}", "Start", TASK_STATUS.COMPLETED)
            try:
                if current_vm.runtime.powerState == 'poweredOn':
                    TASK = current_vm.PowerOff()
                    vmware_commonoperations.async_tasks_wait(
                        compute_client, [TASK])
                add_audit_log(session, task_id, "VMOperation",
                              f"stop_vm:{current_vm.name}", "Success", TASK_STATUS.COMPLETED)
            except Exception as ex:
                print("here we are")
                add_audit_log(session, task_id, "VMOperation",
                              f"stop_vm:{current_vm.name}", f"Failed With Error: {str(ex)}",
                              TASK_STATUS.FAILED)
                exception_list.append({current_vm.name: str(ex)})
            operation_vm_list.remove(current_vm.name)

    if len(operation_vm_list) > 0:
        add_audit_log(session, task_id, "VMOperation", f"stop_vm:{operation_vm_list}",
                      "Failed With Error: no such vm available on requested server",
                      TASK_STATUS.FAILED)

    if exception_list:
        add_audit_log(session, task_id, "VMOperation",
                      f"stop_vm", f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception("Failed To Stop VMware VM:{exception_list}")


def restart_vm(parameters, session, **kwargs):
    # restart the VM operation
    task_id = parameters.get('task_id')
    operation_vm_list = parameters.get('vm_names')
    compute_client = get_vmware_client(parameters)
    LOG.debug(f"Restart VMware VM:{parameters}", {'task_id': task_id})
    add_audit_log(session, task_id, "VMOperation",
                  f"restart_vm:{operation_vm_list}", "Started", TASK_STATUS.COMPLETED)

    content = compute_client.content
    all_vm_obj = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True)
    all_vm_list = all_vm_obj.view
    all_vm_obj.Destroy()

    exception_list = []
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]
    for current_vm in all_vm_list:
        if current_vm.name in operation_vm_list:
            add_audit_log(session, task_id, "VMOperation",
                          f"restart_vm:{current_vm.name}", "Start", TASK_STATUS.COMPLETED)
            try:
                if current_vm.runtime.powerState == 'poweredOn':
                    TASK = current_vm.ResetVM_Task()
                else:
                    TASK = current_vm.PowerOn()
                vmware_commonoperations.async_tasks_wait(
                    compute_client, [TASK])
                add_audit_log(session, task_id, "VMOperation",
                              f"restart_vm:{current_vm.name}", "Success", TASK_STATUS.COMPLETED)
            except Exception as ex:
                add_audit_log(session, task_id, "VMOperation",
                              f"restart_vm:{current_vm.name}", f"Failed With Error: {str(ex)}",
                              TASK_STATUS.FAILED)
                exception_list.append({current_vm.name: str(ex)})
            operation_vm_list.remove(current_vm.name)

    if len(operation_vm_list) > 0:
        add_audit_log(session, task_id, "VMOperation", f"restart_vm:{operation_vm_list}",
                      "Failed With Error: no such vm available on requested server",
                      TASK_STATUS.FAILED)

    if exception_list:
        add_audit_log(session, task_id, "VMOperation",
                      f"restart_vm:{exception_list}", f"Failed With Error: {str(ex)}",
                      TASK_STATUS.FAILED)
        raise Exception("Failed To Restart VMware VM:%s" % exception_list)


def delete_vm(parameters, session, **kwargs):
    _module_name = "VMOperation"
    _function_name = "delete_vm"

    # Delete VM operation
    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware VM:{parameters}", {
              'task_id': task_id})
    operation_vm_list = parameters.get('vm_names')
    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}:{operation_vm_list}", "Started", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    all_vm_obj = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True)
    all_vm_list = all_vm_obj.view
    all_vm_obj.Destroy()

    exception_list = []
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]

    for current_vm in all_vm_list:
        if len(operation_vm_list) > 0 and current_vm.name in operation_vm_list:
            _current_deleting_vm = current_vm.name
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}:{_current_deleting_vm}", "Start", TASK_STATUS.COMPLETED)
            try:
                if current_vm.runtime.powerState == 'poweredOn':
                    TASK1 = current_vm.PowerOffVM_Task()
                    vmware_commonoperations.async_tasks_wait(
                        compute_client, [TASK1])
                TASK2 = current_vm.Destroy_Task()
                vmware_commonoperations.async_tasks_wait(
                    compute_client, [TASK2])
                add_audit_log(session, task_id, f"{_module_name}",
                              f"{_function_name}:{_current_deleting_vm}", "Success",
                              TASK_STATUS.COMPLETED)
            except Exception as ex:
                add_audit_log(session, task_id, f"{_module_name}",
                              f"{_function_name}:{_current_deleting_vm}",
                              f"Failed With Error: {str(ex)}", TASK_STATUS.FAILED)
                exception_list.append({_current_deleting_vm: str(ex)})
            operation_vm_list.remove(_current_deleting_vm)

    if len(operation_vm_list) > 0:
        add_audit_log(session, task_id, f"{_module_name}",
                      f"{_function_name}:{operation_vm_list}",
                      "Failed With Error: These VMs are already deleted or has not been created",
                      TASK_STATUS.FAILED)

    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} On VMware VM:{exception_list}")


def detach_disk(parameters, session, **kwargs):
    # detach_disk VM operation
    _module_name = "VMOperation"
    _function_name = "detach_disk"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Detach Disk:{parameters}", {
              'task_id': task_id})
    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]
    data_disk_names = parameters.get('data_disk_info')
    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}:{operation_vm_list}", "Started", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    all_vm_obj = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True)
    all_vm_list = all_vm_obj.view
    all_vm_obj.Destroy()

    exception_list = []

    if isinstance(data_disk_names, str):
        data_disk_names = [data_disk_names]
    data_disk_names.sort()
    operation_data_disk_names = data_disk_names[::-1]

    for current_vm in all_vm_list:
        if len(operation_vm_list) > 0 and current_vm.name in operation_vm_list:
            _current_vm_name = current_vm.name
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}:{_current_vm_name}", "Start", TASK_STATUS.COMPLETED)
            for _current_disk_name in operation_data_disk_names:
                try:
                    for hard_disk in current_vm.config.hardware.device:
                        if isinstance(hard_disk, vim.vm.device.VirtualDisk) and \
                                hard_disk.deviceInfo.label == _current_disk_name:
                            detach_hdd_device = hard_disk

                            virtual_hdd_spec = vim.vm.device.VirtualDeviceSpec()
                            virtual_hdd_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
                            virtual_hdd_spec.device = detach_hdd_device

                            spec = vim.vm.ConfigSpec()
                            spec.deviceChange = [virtual_hdd_spec]
                            task = current_vm.ReconfigVM_Task(spec=spec)

                            vmware_commonoperations.async_tasks_wait(
                                compute_client, [task])
                            add_audit_log(session, task_id,
                                          f"{_module_name}", f"{_function_name}",
                                          f"Success: for VM: {_current_vm_name} for Disk: {_current_disk_name}",
                                          TASK_STATUS.COMPLETED)
                            data_disk_names.remove(_current_disk_name)
                except Exception as ex:
                    _exception_msg = f"Failed: {_function_name} on VM: {_current_vm_name} " \
                                     f"for Disk:{_current_vm_name}  With Error/Exception: {str(ex)}"
                    add_audit_log(session, task_id, f"{_module_name}",
                                  f"{_function_name}", _exception_msg,
                                  TASK_STATUS.FAILED)
                    exception_list.append({_current_vm_name: _exception_msg})
            if len(data_disk_names) > 0:
                add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                              f"Disk: {data_disk_names} not available in VMware VM: {_current_vm_name}.",
                              TASK_STATUS.FAILED)
            operation_vm_list.remove(_current_vm_name)

    if len(operation_vm_list) > 0:
        add_audit_log(session, task_id, f"{_module_name}",
                      f"{_function_name}:{operation_vm_list}",
                      "Failed With Error: These VMs are already deleted or has not been created",
                      TASK_STATUS.FAILED)

    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} On VMware Detach Disk:{exception_list}")


def delete_vm_snapshot(parameters, session, **kwargs):
    # Delete VM Snapshot operation
    _module_name = "VMOperation"
    _function_name = "delete_vm_snapshot"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Operation:{parameters}", {
              'task_id': task_id})

    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]

    snapshots_name = parameters.get('snapshots')
    if isinstance(snapshots_name, str):
        snapshots_name = [snapshots_name]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", "Started", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content

    for _current_vm_name in operation_vm_list:
        try:
            vm = vmware_commonoperations.get_obj(
                content, [vim.VirtualMachine], _current_vm_name)
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", f"Start {_function_name} Operation for"
                                               f" VM: [{_current_vm_name}] Snapshots: {snapshots_name}",
                          TASK_STATUS.COMPLETED)
            for _snapshot_name in snapshots_name:
                if vm.snapshot:
                    snap_obj = vmware_commonoperations.get_snapshots_by_name_recursively(
                        vm.snapshot.rootSnapshotList, _snapshot_name)
                    if len(snap_obj) == 1:
                        snap_obj = snap_obj[0].snapshot
                        task = snap_obj.RemoveSnapshot_Task(True)
                        vmware_commonoperations.async_tasks_wait(
                            compute_client, [task])
                        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                      f"Success: for VM: {_current_vm_name} for Snapshot: {_snapshot_name}",
                                      TASK_STATUS.COMPLETED)
                    else:
                        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                      f"Failed With Error: For VM : [{_current_vm_name}] "
                                      f"Snapshot:[{_snapshot_name}] already deleted or has not been created.",
                                      TASK_STATUS.FAILED)
                else:
                    add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                  f"Failed With Error: For VM : [{_current_vm_name}] "
                                  f"No any Snapshot Created Yet.", TASK_STATUS.FAILED)
        except RuntimeError:
            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Failed With Error: No Such VM : [{_current_vm_name}] "
                          f"found, So no any snapshot is deleted for this VM.", TASK_STATUS.FAILED)


def change_disk_size(parameters, session, **kwargs):
    # Change Disk Size
    _module_name = "VMOperation"
    _function_name = "change_disk_size"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Resize Disk:{parameters}", {
              'task_id': task_id})
    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]
    data_disk_info = parameters.get('data_disk_info')
    if isinstance(data_disk_info, dict):
        data_disk_info = [data_disk_info]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}:{operation_vm_list}", "Started", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    for _current_vm_name in operation_vm_list:
        vm = vmware_commonoperations.get_obj(
            content, [vim.VirtualMachine], _current_vm_name)
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Start {_function_name} Operation for VM: [{_current_vm_name}] Disks: {data_disk_info}", TASK_STATUS.COMPLETED)
        for _current_disk_info in data_disk_info:
            if _current_disk_info['disk_name'].lower() != "Hard Disk 1".lower():
                try:
                    for resize_hard_disk in vm.config.hardware.device:
                        if isinstance(resize_hard_disk, vim.vm.device.VirtualDisk) and resize_hard_disk.deviceInfo.label == _current_disk_info['disk_name']:
                            GB_TO_BYTES_FACTOR = 1024 ** 3
                            _currect_disk_size_in_gb = resize_hard_disk.capacityInBytes/GB_TO_BYTES_FACTOR

                            virtual_disk_spec = vim.vm.device.VirtualDeviceSpec()
                            virtual_disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                            virtual_disk_spec.device = resize_hard_disk

                            _new_disk_size_GB = _current_disk_info['disk_size_GB']
                            if isinstance(_new_disk_size_GB, str):
                                _new_disk_size_GB = int(_new_disk_size_GB)

                            virtual_disk_spec.device.capacityInBytes = _new_disk_size_GB * GB_TO_BYTES_FACTOR
                            if _currect_disk_size_in_gb > _new_disk_size_GB:
                                raise RuntimeError(f"New Disk size Should not be less then current disk size.\
                                     \n CURRENT DISK SIZE: {_currect_disk_size_in_gb} \
                                     \n NEW DISK SIZE: {_new_disk_size_GB} \
                                     \n NEW DISK INFO:  {_current_disk_info}")

                            spec = vim.vm.ConfigSpec()
                            spec.deviceChange = [virtual_disk_spec]
                            task = vm.ReconfigVM_Task(spec=spec)
                            vmware_commonoperations.async_tasks_wait(
                                compute_client, [task])
                            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                          f"Success: for VM: {_current_vm_name} for Disk: {_current_disk_info}", TASK_STATUS.COMPLETED)
                except Exception as ex:
                    _exception_msg = f"Failed: {_function_name} on VM: {_current_vm_name} for Disk:{_current_disk_info}  With Error/Exception: {str(ex)}"
                    add_audit_log(
                        session, task_id, f"{_module_name}", f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
            else:
                msg = f"Failed: {_function_name} on VM: {_current_vm_name} for Disk:{_current_disk_info}  With Error: Hard Disk 1 Size cannot be Modified."
                add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                              msg, TASK_STATUS.COMPLETED)


def attach_nic(parameters, session, **kwargs):

    _module_name = "VMOperation"
    _function_name = "attach_nic"

    spec = vim.vm.ConfigSpec()
    nic_changes = []

    nic_spec = vim.vm.device.VirtualDeviceSpec()
    nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add

    nic_spec.device = vim.vm.device.VirtualE1000()

    nic_spec.device.deviceInfo = vim.Description()
    nic_spec.device.deviceInfo.summary = 'vCenter API test'

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Operation:{parameters}", {
              'task_id': task_id})

    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]

    network_name = parameters.get('network_name')
    if isinstance(network_name, str):
        network_name = [network_name]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", "Started", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content

    for _current_vm_name in operation_vm_list:
        for current_network_name in network_name:
            try:
                vm = vmware_commonoperations.get_obj(
                    content, [vim.VirtualMachine], _current_vm_name)
                network = vmware_commonoperations.get_obj(
                    content, [vim.Network], current_network_name)
                if network:
                    if isinstance(network, vim.OpaqueNetwork):
                        nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.OpaqueNetworkBackingInfo()
                        nic_spec.device.backing.opaqueNetworkType = network.summary.opaqueNetworkType
                        nic_spec.device.backing.opaqueNetworkId = network.summary.opaqueNetworkId
                    else:
                        nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                        nic_spec.device.backing.useAutoDetect = False
                        nic_spec.device.backing.deviceName = current_network_name

                    nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
                    nic_spec.device.connectable.startConnected = True
                    nic_spec.device.connectable.allowGuestControl = True
                    nic_spec.device.connectable.connected = False
                    nic_spec.device.connectable.status = 'untried'
                    nic_spec.device.wakeOnLanEnabled = True
                    nic_spec.device.addressType = 'assigned'

                    nic_changes.append(nic_spec)
                    spec.deviceChange = nic_changes

                    task = vm.ReconfigVM_Task(spec=spec)

                    vmware_commonoperations.async_tasks_wait(
                        compute_client, [task])

                else:
                    add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                  f"Failed With Error: Network:[{current_network_name}] doesn't exist.", TASK_STATUS.FAILED)

            except RuntimeError:
                add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                              f"Failed With Error: No Such Network : [{current_network_name}] found, So no any network is added to the VM.", TASK_STATUS.FAILED)


def detach_nic(parameters, session, **kwargs):

    _module_name = "VMOperation"
    _function_name = "detach_nic"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Operation:{parameters}", {
              'task_id': task_id})

    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]

    nic_label = parameters.get('nic_label')
    if isinstance(nic_label, str):
        nic_label = [nic_label]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", "Started", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content

    for _current_vm_name in operation_vm_list:
        for current_nic_label in nic_label:

            #nic_prefix_label = 'Network adapter '
            #nic_label = nic_prefix_label + str(nic_number)

            try:
                vm = vmware_commonoperations.get_obj(
                    content, [vim.VirtualMachine], _current_vm_name)
                add_audit_log(session, task_id, f"{_module_name}",
                              f"{_function_name}", f"Start {_function_name} Operation for VM: [{_current_vm_name}] Nic: {current_nic_label}", TASK_STATUS.COMPLETED)

                for dev in vm.config.hardware.device:
                    if isinstance(dev, vim.vm.device.VirtualEthernetCard) and dev.deviceInfo.label == current_nic_label:
                        virtual_nic_device = dev

                if virtual_nic_device:

                    virtual_nic_spec = vim.vm.device.VirtualDeviceSpec()
                    virtual_nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
                    virtual_nic_spec.device = virtual_nic_device

                    spec = vim.vm.ConfigSpec()
                    spec.deviceChange = [virtual_nic_spec]
                    task = vm.ReconfigVM_Task(spec=spec)
                    vmware_commonoperations.async_tasks_wait(
                        compute_client, [task])
                else:
                    add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                  f"Failed With Error: For VM : [{_current_vm_name}] Nic:[{current_nic_label}] already deleted or has not been created.", TASK_STATUS.FAILED)

            except RuntimeError:
                add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                              f"Failed With Error: No Such VM : [{_current_vm_name}] found, So no any nic is deleted for this VM.", TASK_STATUS.FAILED)

def add_disk(parameters, session, **kwargs):
    # add_disk VM operation
    _module_name = "VMOperation"
    _function_name = "add_disk"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Add Disk:{parameters}",
              {'task_id': task_id})

    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]

    data_disk_info = parameters.get('data_disk_info')
    if data_disk_info:
        add_audit_log(session, task_id, f"{_module_name}",
                      f"{_function_name}:{operation_vm_list}", "Started",
                      TASK_STATUS.COMPLETED)

        compute_client = get_vmware_client(parameters)
        content = compute_client.content

        exception_list = []
        ids = []
        for _current_vm_name in operation_vm_list:
            index = operation_vm_list.index(_current_vm_name)
            try:
                _current_vm_obj = vmware_commonoperations.get_obj(
                    content, [vim.VirtualMachine], _current_vm_name)
                current_vm = _current_vm_obj
                unit_number = 0
                controller = None
                for device in _current_vm_obj.config.hardware.device:
                    if hasattr(device.backing, 'fileName'):
                        unit_number = int(device.unitNumber) + 1
                        # unit_number 7 reserved for scsi controller
                        if unit_number == 7:
                            unit_number += 1
                        if unit_number >= 16:
                            raise RuntimeError(
                                f"we don't support this many disks unit_number:[{unit_number}]")
                    if isinstance(device, vim.vm.device.VirtualSCSIController):
                        controller = device
                if controller is None:
                    raise RuntimeError("Disk SCSI controller not found!")

                spec = vim.vm.ConfigSpec()
                for disk_info in data_disk_info:
                    random_num = randint(10000, 99999)
                    disk_size = disk_info.get('disk_size_GB')
                    disk_format = disk_info.get('disk_format', 'thin')
                    disk_name = "%s_data_disk_%s" % (_current_vm_name, random_num)
                    add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                  f"Start for VM:[{_current_vm_name} Disks:[{disk_name}]]",
                                  TASK_STATUS.COMPLETED)
                    new_disk_kb = int(disk_size) * 1024 * 1024
                    disk_spec = vim.vm.device.VirtualDeviceSpec()
                    disk_spec.fileOperation = "create"
                    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
                    disk_spec.device = vim.vm.device.VirtualDisk()
                    disk_spec.device.backing = \
                        vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
                    if disk_format == 'thin':
                        disk_spec.device.backing.thinProvisioned = True
                    disk_spec.device.backing.diskMode = 'persistent'
                    disk_spec.device.unitNumber = unit_number
                    disk_spec.device.capacityInKB = new_disk_kb
                    disk_spec.device.controllerKey = controller.key
                    dev_changes = [disk_spec]
                    spec.deviceChange = dev_changes
                    # Sending the request
                    task = current_vm.ReconfigVM_Task(spec=spec)
                    vmware_commonoperations.async_tasks_wait(
                        compute_client, [task])
                    add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                  f"Succeed: {_function_name} for VM:[{_current_vm_name} "
                                  f"for Disk:[{disk_name}]", TASK_STATUS.COMPLETED)
                    unit_number += 1
                # for device in current_vm.config.hardware.device:
                #     if type(device).__name__ == 'vim.vm.device.VirtualDisk':
                #         disk_id = "\"//%s//%s\"" % (parameters.get('dc_name'), device.backing.fileName)
                #         LOG.debug("Disk id is:%s" % disk_id, {'task_id': task_id})
                #         ids.append(disk_id)
                # if ids:
                #     tf_obj = TerraformClass(config=kwargs.get('config'), db_conn=session,
                #                             task_id=task_id, env_vars=kwargs.get('env_vars'))
                #     tf_obj(state="add_disk", payload=parameters, resource_ids=ids,
                #            index=index)

            except Exception as ex:
                _exception_msg = f"Failed: {_function_name} on VM: {_current_vm_name} for " \
                                 f"add Disk with Error/Exception: {str(ex)}"
                exception_list.append({_current_vm_name: _exception_msg})
                add_audit_log(session, task_id, f"{_module_name}",
                              f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
        if exception_list:
            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
            raise Exception(f"Failed To Perform {_module_name}:{_function_name} "
                f"On VMware Add Disk:{exception_list}")
    else:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Disk information not available", TASK_STATUS.COMPLETED)


def attach_disk(parameters, session, **kwargs):
    # attach_disk VM operation
    _module_name = "VMOperation"
    _function_name = "attach_disk"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Attach Disk:{parameters}", {
              'task_id': task_id})

    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]

    operation_data_disk_names = parameters.get('disk_name')
    if isinstance(operation_data_disk_names, str):
        operation_data_disk_names = [operation_data_disk_names]

    data_store_name = parameters.get('data_datastore_name')

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}:{operation_vm_list}", "Started", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content

    exception_list = []
    for _current_vm_name in operation_vm_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Start for VM:[{_current_vm_name} Disks:[{operation_data_disk_names}]]",
                      TASK_STATUS.COMPLETED)
        try:
            _current_vm_obj = vmware_commonoperations.get_obj(
                content, [vim.VirtualMachine], _current_vm_name)
            current_vm = _current_vm_obj

            unit_number = 0
            controller = None
            for device in _current_vm_obj.config.hardware.device:
                if hasattr(device.backing, 'fileName'):
                    unit_number = int(device.unitNumber) + 1
                    # unit_number 7 reserved for scsi controller
                    if unit_number == 7:
                        unit_number += 1
                    if unit_number >= 16:
                        raise RuntimeError(
                            f"we don't support this many disks unit_number:[{unit_number}]")
                if isinstance(device, vim.vm.device.VirtualSCSIController):
                    controller = device
            if controller is None:
                raise RuntimeError("Disk SCSI controller not found!")

            for _current_disk_name in operation_data_disk_names:
                spec = vim.vm.ConfigSpec()
                disk_spec = vim.vm.device.VirtualDeviceSpec()
                disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
                disk_spec.device = vim.vm.device.VirtualDisk()
                disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
                disk_spec.device.backing.diskMode = 'persistent'
                disk_spec.device.backing.fileName = f"[{data_store_name}] {_current_disk_name}"
                disk_spec.device.unitNumber = unit_number
                disk_spec.device.controllerKey = controller.key
                # Creating change list
                dev_changes = [disk_spec]
                spec.deviceChange = dev_changes
                # Sending the request
                task = current_vm.ReconfigVM_Task(spec=spec)
                vmware_commonoperations.async_tasks_wait(
                    compute_client, [task])
                add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                              f"Succeed: {_function_name} for VM:[{_current_vm_name} "
                              f"for Disk:[{_current_disk_name}]", TASK_STATUS.COMPLETED)
                unit_number += 1
        except Exception as ex:
            _exception_msg = f"Failed: {_function_name} on VM: {_current_vm_name} for " \
                             f"attach Disk with Error/Exception: {str(ex)}"
            exception_list.append({_current_vm_name: _exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
                          
    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} On VMware Attach Disk:{exception_list}")

            
def change_vm_size(parameters, session, **kwargs):
    # Change VM Size
    _module_name = "VMOperation"
    _function_name = "change_vm_size"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Resize VM:{parameters}", {
              'task_id': task_id})
    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]
    vm_size_info = parameters.get('vm_size_info')

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}:{operation_vm_list}", "Started", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    for _current_vm_name in operation_vm_list:
        try:
            vm = vmware_commonoperations.get_obj(
                content, [vim.VirtualMachine], _current_vm_name)
            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Start {_function_name} Operation for VM: [{_current_vm_name}] Disks: {vm_size_info}", TASK_STATUS.COMPLETED)

            _current_vm_memorySizeMB = vm.summary.config.memorySizeMB/1024
            _current_vm_numCpu = vm.summary.config.numCpu

            _new_memorySizeGB = vm_size_info.get('memory_size_gb', None)
            _new_memorySizeMB = None
            _new_vm_numCpu = vm_size_info.get('cpu_cores', None)

            if isinstance(_new_memorySizeGB, str):
                _new_memorySizeMB = int(_new_memorySizeGB)*1024
            if isinstance(_new_vm_numCpu, str):
                _new_vm_numCpu = int(_new_vm_numCpu)

            vm_spec = vim.vm.ConfigSpec()
            if _new_memorySizeMB:
                vm_spec.memoryMB = _new_memorySizeMB
            if _new_vm_numCpu:
                vm_spec.numCPUs = _new_vm_numCpu

            task = vm.Reconfigure(vm_spec)
            vmware_commonoperations.async_tasks_wait(compute_client, [task])
            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: Changed VM Size for VM: {_current_vm_name} from \n \
                              Current VM Size: MEMORY: {_current_vm_memorySizeMB}GB CPU Cores: {_current_vm_numCpu} \
                                  \n To New VM Size : {vm_size_info}", TASK_STATUS.COMPLETED)
        except Exception as ex:
            _exception_msg = f"Failed: {_function_name} on VM: {_current_vm_name} for New VM Size :{vm_size_info}  With Error/Exception: {str(ex)}"
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)


def disable_cpu_hot_plug(parameters, session, **kwargs):

    _module_name = "VMOperation"
    _function_name = "disable_cpu_hot_plug"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Operation:{parameters}", {
              'task_id': task_id})

    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: {operation_vm_list}", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content

    for _current_vm_name in operation_vm_list:
        add_audit_log(session, task_id, f"{_module_name}",
                      f"{_function_name}", f"Start {_function_name} Operation for VM: [{_current_vm_name}]", TASK_STATUS.COMPLETED)
        try:
            vm = vmware_commonoperations.get_obj(
                content, [vim.VirtualMachine], _current_vm_name)

            spec = vim.vm.ConfigSpec()
            spec.cpuHotAddEnabled = False

            task = vm.ReconfigVM_Task(spec=spec)
            vmware_commonoperations.async_tasks_wait(compute_client, [task])

            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: {_module_name} for VM: {_current_vm_name}", TASK_STATUS.COMPLETED)
        except Exception as e:
            _exception_msg = f"Failed: {_function_name} on VM: {_current_vm_name} With Error/Exception: {str(e)}"
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)


def enable_cpu_hot_plug(parameters, session, **kwargs):

    _module_name = "VMOperation"
    _function_name = "enable_cpu_hot_plug"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Operation:{parameters}", {
              'task_id': task_id})

    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: {operation_vm_list}", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content

    for _current_vm_name in operation_vm_list:
        add_audit_log(session, task_id, f"{_module_name}",
                      f"{_function_name}", f"Start {_function_name} Operation for VM: [{_current_vm_name}]", TASK_STATUS.COMPLETED)
        try:
            vm = vmware_commonoperations.get_obj(
                content, [vim.VirtualMachine], _current_vm_name)

            spec = vim.vm.ConfigSpec()
            spec.cpuHotAddEnabled = True

            task = vm.ReconfigVM_Task(spec=spec)
            vmware_commonoperations.async_tasks_wait(compute_client, [task])

            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: {_module_name} for VM: {_current_vm_name}", TASK_STATUS.COMPLETED)
        except Exception as e:
            _exception_msg = f"Failed: {_function_name} on VM: {_current_vm_name} With Error/Exception: {str(e)}"
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)


def enable_memory_hot_plug(parameters, session, **kwargs):
    # Enable Memory Hot Plug In VM
    _module_name = "VMOperation"
    _function_name = "enable_memory_hot_plug"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} Enable Memory Hot Plug In VM:{parameters}", {
              'task_id': task_id})
    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: {operation_vm_list}", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    exception_list = []
    for _current_vm_name in operation_vm_list:
        add_audit_log(session, task_id, f"{_module_name}",
                      f"{_function_name}", f"Start {_function_name} Operation for VM: [{_current_vm_name}]", TASK_STATUS.COMPLETED)
        try:
            vm = vmware_commonoperations.get_obj(
                content, [vim.VirtualMachine], _current_vm_name)

            vm_spec = vim.vm.ConfigSpec()
            vm_spec.memoryHotAddEnabled = True

            task = vm.ReconfigVM_Task(spec=vm_spec)
            vmware_commonoperations.async_tasks_wait(compute_client, [task])

            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: for VM: {_current_vm_name} Enabled Memory Hot Plug", TASK_STATUS.COMPLETED)
        except Exception as e:
            _exception_msg = f"Failed: {_function_name} on VM: {_current_vm_name} With Error/Exception: {str(e)}"
            exception_list.append({_current_vm_name: _exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} On VM:{exception_list}")


def disable_memory_hot_plug(parameters, session, **kwargs):
    # Disable Memory Hot Plug In VM
    _module_name = "VMOperation"
    _function_name = "disable_memory_hot_plug"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} Disable Memory Hot Plug In VM:{parameters}", {
              'task_id': task_id})
    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: {operation_vm_list}", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    exception_list = []
    for _current_vm_name in operation_vm_list:
        add_audit_log(session, task_id, f"{_module_name}",
                      f"{_function_name}", f"Start {_function_name} Operation for VM: [{_current_vm_name}]", TASK_STATUS.COMPLETED)
        try:
            vm = vmware_commonoperations.get_obj(
                content, [vim.VirtualMachine], _current_vm_name)

            vm_spec = vim.vm.ConfigSpec()
            vm_spec.memoryHotAddEnabled = False

            task = vm.ReconfigVM_Task(spec=vm_spec)
            vmware_commonoperations.async_tasks_wait(compute_client, [task])

            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: for VM: {_current_vm_name} Disabled Memory Hot Plug", TASK_STATUS.COMPLETED)
        except Exception as e:
            _exception_msg = f"Failed: {_function_name} on VM: {_current_vm_name} With Error/Exception: {str(e)}"
            exception_list.append({_current_vm_name: _exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} On VM:{exception_list}")


def relocate_vm(parameters, session, **kwargs):
    # Relocate VM from one host to another
    _module_name = "VMOperation"
    _function_name = "relocate_vm"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} Relocate VM from one host to another :{parameters}", {
              'task_id': task_id})
    operation_vm_list = parameters.get('vm_name')
    destination_host = parameters.get('destination_host')
    destination_datastore = parameters.get('destination_datastore')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: with PARAMETERS:{parameters}", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    exception_list = []

    for _current_vm_name in operation_vm_list:
        add_audit_log(session, task_id, f"{_module_name}",
                      f"{_function_name}", f"Start {_function_name} Operation for VM: [{_current_vm_name}] to HOST: {destination_datastore} DATASTORE: {destination_datastore}", TASK_STATUS.COMPLETED)
        try:
            _current_vm_obj = vmware_commonoperations.get_obj(
                content, [vim.VirtualMachine], _current_vm_name)
            relocate_vm_spec = vim.VirtualMachineRelocateSpec()
            current_host = _current_vm_obj.runtime.host.name
            if current_host == destination_host:
                raise Exception(
                    f"Destination host Address Cannot be same as Current host address. VM Name: {_current_vm_name} CURRENT_HOST:{current_host}")
            destination_host_obj = vmware_commonoperations.get_obj(
                content, [vim.HostSystem], destination_host)
            relocate_vm_spec.host = destination_host_obj

            resource_pool_obj = destination_host_obj.parent.resourcePool
            relocate_vm_spec.pool = resource_pool_obj

            if destination_datastore is not None:
                destination_datastore_obj = vmware_commonoperations.get_obj(
                    content, [vim.Datastore], destination_datastore)
                relocate_vm_spec.datastore = destination_datastore_obj

                all_vm_disks_locater = []
                for device in _current_vm_obj.config.hardware.device:
                    if type(device).__name__ == "vim.vm.device.VirtualDisk" \
                            and hasattr(device.backing, 'fileName'):
                        disk = device
                        locator = vim.vm.RelocateSpec.DiskLocator()
                        locator.diskBackingInfo = disk.backing
                        locator.diskId = int(disk.key)
                        locator.datastore = destination_datastore_obj
                        all_vm_disks_locater.append(locator)

                relocate_vm_spec.disk = all_vm_disks_locater
            task = _current_vm_obj.RelocateVM_Task(relocate_vm_spec)
            vmware_commonoperations.async_tasks_wait(compute_client, [task])

            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: for VM: {_current_vm_name} Relocated to HOST: {destination_datastore} DATASTORE: {destination_datastore}", TASK_STATUS.COMPLETED)
        except RuntimeError:
            _exception_msg = f"Failed With Error: No Such VM : [{_current_vm_name}] found."
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.COMPLETED)
            exception_list.append({_current_vm_name: _exception_msg})
        except Exception as e:
            _exception_msg = f"Failed: {_function_name} on VM: {_current_vm_name} Relocated to HOST: {destination_datastore} DATASTORE: {destination_datastore} With Error/Exception: {str(e)}"
            exception_list.append({_current_vm_name: _exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} On VMware VMs:{exception_list}")


def upgrade_virtual_machine(parameters, session, **kwargs): 
    # UPGRADE VM
    _module_name = "VMOperation"
    _function_name = "upgrade_vm"
    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Upgrade VM:{parameters}", {
              'task_id': task_id})
    operation_vm_list = parameters.get('vm_upgrade_info')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [{'vm_name' : operation_vm_list,
                              'release' : "NA"}]
    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}:{operation_vm_list}", "Started", TASK_STATUS.COMPLETED)
    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    exception_list = []
    for current_vm in operation_vm_list:
        vm_name = current_vm.get('vm_name')
        release = current_vm.get('release')
        try:        
            vm = vmware_commonoperations.get_obj(content, 
                                                 [vim.VirtualMachine], 
                                                 vm_name)
            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Start: {_function_name} Operation for VM: [{vm_name}]", 
                          TASK_STATUS.COMPLETED)
            if release != "NA":
                print("New version will be %s" % release)
                version = "vmx-{:02d}".format(release)
            else:
                version = None

            if vm.runtime.powerState == 'poweredOn':
                stopvm_parameters = parameters
                stopvm_parameters['vm_names'] = vm_name
                stop_vm(stopvm_parameters, session)  
            try:
                task = vm.UpgradeVM_Task(version)
                vmware_commonoperations.async_tasks_wait(compute_client, [task])
                add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                              f"Success: {_function_name} Operation for VM: [{vm_name}]", 
                              TASK_STATUS.COMPLETED)
            except vim.fault.AlreadyUpgraded:
                _exception_msg = f"VM [{vm_name}] is already upgraded."
                add_audit_log(session, task_id, f"{_module_name}",
                              f"{_function_name}", _exception_msg, TASK_STATUS.COMPLETED)
                exception_list.append({vm_name: _exception_msg})
        except:
            _exception_msg = f"Failed With Error: No Such VM : [{vm_name}] found."
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.COMPLETED)
            exception_list.append({vm_name: _exception_msg})                
        
        if exception_list:
            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
            raise Exception(
                f"Failed To Perform {_module_name}:{_function_name} On VMware VMs:{exception_list}")


def add_note(parameters, session, **kwargs):

    _module_name = "VMOperation"
    _function_name = "add_note"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Operation:{parameters}", {
              'task_id': task_id})

    operation_vm_list = parameters.get('vm_name')
    if isinstance(operation_vm_list, str):
        operation_vm_list = [operation_vm_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: {operation_vm_list}", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content

    for _current_vm_name in operation_vm_list:
        add_audit_log(session, task_id, f"{_module_name}",
                      f"{_function_name}", f"Start {_function_name} Operation for VM: [{_current_vm_name}]", TASK_STATUS.COMPLETED)
        try:
            vm = vmware_commonoperations.get_obj(
                content, [vim.VirtualMachine], _current_vm_name)
            
            note = parameters.get('vm_note')
            spec = vim.vm.ConfigSpec()
            spec.annotation = note

            task = vm.ReconfigVM_Task(spec=spec)
            vmware_commonoperations.async_tasks_wait(compute_client, [task])

            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: {_module_name} for VM: {_current_vm_name}", TASK_STATUS.COMPLETED)
        except Exception as e:
            _exception_msg = f"Failed: {_function_name} on VM: {_current_vm_name} With Error/Exception: {str(e)}"
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)


def set_vm_storage_policy(parameters, session, **kwargs): 
    ##### SET STORAGE POLICY FOR A VM #####
    _module_name = "VMOperation"
    _function_name = "set_vm_storage_policy"
    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Set VM Storage Policy:{parameters}", {
          'task_id': task_id})
    operation_lst = parameters.get("set_storage_policy_info")
    add_audit_log(session, task_id, f"{_module_name}",
              f"{_function_name}:{operation_lst}", "Started", TASK_STATUS.COMPLETED)
    client = get_vmware_client(parameters)
    exception_list = []
    
    def check_storage_profile_associated(profile_manager, ref, name):
        """Get name of VMware Storage Policy profile associated with
            the specified entities
        :param profileManager: A VMware Storage Policy Service manager object
        :type profileManager: pbm.profile.ProfileManager
        :param ref: A server reference to a virtual machine, virtual disk,
            or datastore
        :type ref: pbm.ServerObjectRef
        :param name: A VMware Storage Policy profile name
        :type name: str
        :returns: True if VMware Storage Policy profile with the specified
            name associated with the specified entities
        :rtype: bool
        """
        profile_ids = profile_manager.PbmQueryAssociatedProfile(ref)
        if len(profile_ids) > 0:
            profiles = profile_manager.PbmRetrieveContent(profileIds=profile_ids)
            for profile in profiles:
                if profile.name == name:
                    return True
        return False

    for current_vm in operation_lst:
        vm_name = current_vm.get("vm_name")
        policy_name = current_vm.get("policy_name")    
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Start: {_function_name} Operation for VM: [{vm_name}]", 
                      TASK_STATUS.COMPLETED)        
        try :            
            ##### Connect to the VMware Storage Policy Server #####
            stub_adapter = client._stub
            if hasattr(ssl, '_create_unverified_context'):
                ssl_context = ssl._create_unverified_context()
            else:
                ssl_context = None 

            VmomiSupport.GetRequestContext()["vcSessionCookie"] = stub_adapter.cookie.split('"')[1]
            hostname = stub_adapter.host.split(":")[0]
            pbm_stub = SoapStubAdapter(
                host=hostname,
                version="pbm.version.version1",
                path="/pbm/sdk",
                poolSize=0,
                sslContext=ssl_context)
            pbm_si = pbm.ServiceInstance("ServiceInstance", pbm_stub)
            pbm_content = pbm_si.RetrieveContent()
            profile_manager = pbm_content.profileManager
        except Exception as ex:
            _exception_msg = f"Connect to the VMware Storage Policy Server Exception : [{ex}]"
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
            exception_list.append({vm_name: _exception_msg})
        
        try:
            #### Search vmware storage policy profile by name ####
            profile_ids = profile_manager.PbmQueryProfile(
                resourceType=pbm.profile.ResourceType(resourceType="STORAGE"),
                profileCategory="REQUIREMENT"
            )
            if len(profile_ids) > 0:
                storage_profiles = profile_manager.PbmRetrieveContent(
                    profileIds=profile_ids)

            storage_profile = None
            for storageProfile in storage_profiles:
                if storageProfile.name == policy_name:
                    storage_profile = storageProfile
            if not storage_profile:
                _exception_msg = f'Unable to find storage profile with name - {policy_name}'
                exception_list.append({vm_name: _exception_msg})
                add_audit_log(session, task_id, f"{_module_name}",
                              f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
                raise SystemExit(_exception_msg)
        except Exception as ex:
            _exception_msg = f"Search vmware storage policy profile Exception : [{ex}]"
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
            exception_list.append({vm_name: _exception_msg})
        
        try:
            ##### Search virtual machine by name #####
            content = client.content
            root_folder = content.rootFolder
            obj_view = content.viewManager.CreateContainerView(root_folder, 
                                                               [vim.VirtualMachine], True)
            vm_list = obj_view.view
            obj_view.Destroy()
            obj_list = []
            for vm in vm_list:
                if vm.name == vm_name:
                    obj_list.append(vm)
        except Exception as ex:
            _exception_msg = f"Search virtual machine Exception : [{ex}]"
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
            exception_list.append({vm_name: _exception_msg})
        
        if not obj_list:
            _exception_msg = f"No such virtual machine found."
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.COMPLETED)
            exception_list.append({vm_name: _exception_msg})
        else:
            for vm in obj_list:
                pm_object_type = pbm.ServerObjectRef.ObjectType("virtualMachine")
                pm_ref = pbm.ServerObjectRef(key=vm._moId, objectType=pm_object_type)
                if not check_storage_profile_associated(profile_manager, pm_ref, policy_name):
                    add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                  f"Start: {_function_name} [{policy_name}] Operation for Vm [{vm}]", 
                                  TASK_STATUS.COMPLETED)
                    try:
                        ##### Set vmware storage policy profile to VM Home #####
                        spec = vim.vm.ConfigSpec()
                        profile_specs = []
                        profile_spec = vim.vm.DefinedProfileSpec()
                        profile_spec.profileId = storage_profile.profileId.uniqueId
                        profile_specs.append(profile_spec)
                        spec.vmProfile = profile_specs
                        task = vm.ReconfigVM_Task(spec)
                        vmware_commonoperations.async_tasks_wait(client, [task])
                        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                  f"Success: {_function_name} Operation for VM: [{vm}]", 
                                  TASK_STATUS.COMPLETED)
                    except Exception as ex:
                        _exception_msg = 'VM reconfiguration task error: {}'.format(ex)
                        exception_list.append({vm_name: _exception_msg})
                        add_audit_log(session, task_id, f"{_module_name}",
                                      f"{_function_name}", _exception_msg, TASK_STATUS.COMPLETED)
                else:
                    _exception_msg = f'Set VM Home policy: Nothing to do'
                    add_audit_log(session, task_id, f"{_module_name}",
                                  f"{_function_name}", _exception_msg, TASK_STATUS.COMPLETED)
                    exception_list.append({vm_name: _exception_msg})    
    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(f"Failed To Perform {_module_name}:{_function_name}:{exception_list}")

def validate_host_details(parameters, host_details):
    print("Validate host details:%s" % host_details)
    required_memory = parameters.get('memory')*1024
    required_cpu = parameters.get('num_cpus')
    os_storage_size = parameters.get('os_storage_size')
    data_storage_size = parameters.get('data_storage_size')
    required_storage = os_storage_size + data_storage_size

    host_free_memory = host_details.get('free_mem')
    host_all_memory = host_details.get('all_mem')
    host_all_10 = int((host_all_memory*10)/100)
    free_memory = host_free_memory - host_all_10
    if free_memory < required_memory:
        return None

    host_free_cpu = host_details.get('cpu')
    host_all_10 = int((host_free_cpu * 10) / 100)
    free_cpu = host_free_cpu - host_all_10
    if free_cpu < required_cpu:
        return None
    datastore_name = None
    datastore_info = host_details.get('datastore_info')
    for datastore in datastore_info:
        capacity = datastore.get('capacity')
        freespace = datastore.get('freespace')
        free_20 = int((capacity*20)/100)
        free_storage = freespace - free_20
        if free_storage > required_storage:
            datastore_name = datastore.get('name')
            break
    return datastore_name

def get_host_details(parameters):
    _module_name = "VMOperation"
    _function_name = "get_host_details"
    esxi_host = parameters.get('esxi_host')

    try:
        compute_client = get_vmware_client(parameters)
        content = compute_client.content
        host_view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.HostSystem], True)
        obj = [host for host in host_view.view]
        host_view.Destroy()

        datastore_view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.Datastore], True)
        datastore_obj = [datastore for datastore in datastore_view.view]
        datastore_view.Destroy()
        host_details = {}
        host_details['datastore_info'] = []

        # vm_view = content.viewManager.CreateContainerView(
        #     content.rootFolder, [vim.VirtualMachine], True)
        # vm_obj = [vm for vm in vm_view.view]
        # vm_view.Destroy()

        datastore_names = []
        for host in obj:
            cpu = host.hardware.cpuInfo.numCpuCores
            mem_usage = host.summary.quickStats.overallMemoryUsage
            all_mem = int(host.hardware.memorySize / 1024 / 1024)
            free_mem = all_mem - mem_usage
            if host.name == esxi_host:
                cpu_in_use = 0
                host_details['name'] = host.name
                host_details['free_mem'] = free_mem
                host_details['all_mem'] = all_mem
                host_details['cpu'] = cpu
                host_details['host'] = host.summary.host

                storage_system = host.configManager.storageSystem
                host_file_sys_vol_mount_info = \
                    storage_system.fileSystemVolumeInfo.mountInfo
                # Map all filesystems
                for host_mount_info in host_file_sys_vol_mount_info:
                    if host_mount_info.volume.type == "VMFS":
                        datastore_names.append(host_mount_info.volume.name)
                # for vm in vm_obj:
                #     if vm.summary.runtime.powerState == "poweredOn":
                #         summary = vm.summary
                #         if summary.runtime.host == host.summary.host:
                #             cpu_in_use += summary.config.numCpu
                # host_details['free_cpu'] = cpu - cpu_in_use

        for ds_obj in datastore_obj:
            summary = ds_obj.summary
            ds_capacity = summary.capacity
            ds_freespace = summary.freeSpace
            if summary.name in datastore_names:
                datastore_info = {}
                datastore_info['name'] = summary.name
                datastore_info['capacity'] = ds_capacity
                datastore_info['freespace'] = ds_freespace
                host_details['datastore_info'].append(datastore_info)
        print(host_details)
        return host_details
    except Exception as ex:
        raise Exception("Failed to get host details:%s" % str(ex))
