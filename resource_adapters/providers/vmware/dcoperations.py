from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from resource_adapters.utils.vmware_clients import get_vmware_client
import resource_adapters.providers.vmware.commonoperations as vmware_commonoperations
from pyVmomi import vim
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
    # delete data data disk
    _module_name = "DCoperations"
    _function_name = "delete_disk"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Data Disk:{parameters}", {
              'task_id': task_id})
    operation_disk_path_list = parameters.get('disk_path')
    _datastore_name = parameters.get('datastore_name')
    _datacenter_name = parameters.get('datacenter_name')
    if isinstance(operation_disk_path_list, str):
        operation_disk_path_list = [operation_disk_path_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: {operation_disk_path_list}", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content

    for _disk_path in operation_disk_path_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Start {_function_name} Operation On Disk: {_disk_path}", TASK_STATUS.COMPLETED)
        try:
            _dist_disk = f"[{_datastore_name}] {_disk_path}"
            diskManager = content.virtualDiskManager
            _datacenter_obj = vmware_commonoperations.get_obj(
                content, [vim.Datacenter], _datacenter_name)
            task = diskManager.DeleteVirtualDisk_Task(
                name=_dist_disk, datacenter=_datacenter_obj)
            vmware_commonoperations.async_tasks_wait(compute_client, [task])
            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: Deleted DISK: {_disk_path} from DATASTORE: {_datastore_name} DATACENTER: {_datacenter_name}", TASK_STATUS.COMPLETED)
        except Exception as ex:
            _exception_msg = f"Failed: {_function_name} on Disk: {_disk_path} With Error/Exception: {str(ex)}"
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)


def delete_resource_pool(parameters, session, **kwargs):
    # Delete Resource Pool
    _module_name = "DCoperations"
    _function_name = "delete_resource_pool"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} Delete Resource Pool: {parameters}", {
              'task_id': task_id})
    operation_resource_pool_list = parameters.get('resource_pool')
    if isinstance(operation_resource_pool_list, str):
        operation_resource_pool_list = [operation_resource_pool_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: with PARAMETERS:{parameters}", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    exception_list = []

    for _current_resource_pool in operation_resource_pool_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Start {_function_name} Operation for Resource Pool: [{_current_resource_pool}]", TASK_STATUS.COMPLETED)
        try:
            _current_resource_pool_obj = vmware_commonoperations.get_obj(
                content, [vim.ResourcePool], _current_resource_pool)

            task = _current_resource_pool_obj.Destroy_Task()
            vmware_commonoperations.async_tasks_wait(compute_client, [task])

            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: Deleted Resource Pool: {_current_resource_pool}", TASK_STATUS.COMPLETED)
        except RuntimeError:
            _exception_msg = f"Failed With Error: No Such Resource Pool: [{_current_resource_pool}] found."
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.COMPLETED)
            exception_list.append({_current_resource_pool: _exception_msg})
        except Exception as e:
            _exception_msg = f"Failed: {_function_name} on Resource Pool: {_current_resource_pool} With Error/Exception: {str(e)}"
            exception_list.append({_current_resource_pool: _exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} On Resource Pool:{exception_list}")


def edit_resource_pool(parameters, session, **kwargs):
    # Edit Resource Pool
    _module_name = "DCoperations"
    _function_name = "edit_resource_pool"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} Edit Resource Pool: {parameters}", {
              'task_id': task_id})
    operation_resource_pool_list = parameters.get('resource_pool')
    if isinstance(operation_resource_pool_list, str):
        operation_resource_pool_list = [operation_resource_pool_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: with PARAMETERS:{parameters}", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    exception_list = []

    for _current_resource_pool_config in operation_resource_pool_list:
        _current_resource_pool_name = _current_resource_pool_config.get(
            'resource_pool_name')
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Start {_function_name} Operation for Resource Pool: [{_current_resource_pool_name}]", TASK_STATUS.COMPLETED)
        try:
            _current_resource_pool_obj = vmware_commonoperations.get_obj(
                content, [vim.ResourcePool], _current_resource_pool_name)

            resource_pool_spec = vim.ResourceConfigSpec()

            # configure all cpu config
            cpuAllocation_spec = vim.ResourceAllocationInfo()
            if _current_resource_pool_config.get('cpu_limit'):
                cpuAllocation_spec.limit = _current_resource_pool_config.get(
                    'cpu_limit')
            if _current_resource_pool_config.get('cpu_expandable'):
                cpuAllocation_spec.expandableReservation = _current_resource_pool_config.get(
                    'cpu_expandable')
            if _current_resource_pool_config.get('cpu_reservation'):
                cpuAllocation_spec.reservation = _current_resource_pool_config.get(
                    'cpu_reservation')

            cpuAllocation_share = vim.SharesInfo()
            SHARESINFO_LEVEL = ['high', 'low', 'normal', 'custom']

            cpu_share_level = _current_resource_pool_config.get(
                'cpu_share_level').lower()
            if cpu_share_level is not None and cpu_share_level in SHARESINFO_LEVEL:
                if cpu_share_level == 'custom':
                    cpuAllocation_share.level = cpu_share_level
                    if _current_resource_pool_config.get('cpu_shares'):
                        cpuAllocation_share.shares = _current_resource_pool_config.get(
                            'cpu_shares')
                    else:
                        raise RuntimeError(
                            f"For CPU Custom Share Level, Value of Shares must be provided with parameter [cpu_shares].")
                else:
                    cpuAllocation_share.level = cpu_share_level
            else:
                raise RuntimeError(
                    f"SHARE LEVEL Must be only {SHARESINFO_LEVEL}. Provided cpu_share_level: {cpu_share_level}")

            cpuAllocation_spec.shares = cpuAllocation_share

            resource_pool_spec.cpuAllocation = cpuAllocation_spec

            # configure all Memory config
            memoryAllocation_spec = vim.ResourceAllocationInfo()
            if _current_resource_pool_config.get('memory_limit'):
                memoryAllocation_spec.limit = _current_resource_pool_config.get(
                    'memory_limit')
            if _current_resource_pool_config.get('memory_expandable'):
                memoryAllocation_spec.expandableReservation = _current_resource_pool_config.get(
                    'memory_expandable')
            if _current_resource_pool_config.get('memory_reservation'):
                memoryAllocation_spec.reservation = _current_resource_pool_config.get(
                    'memory_reservation')

            memoryAllocation_share = vim.SharesInfo()
            SHARESINFO_LEVEL = ['high', 'low', 'normal', 'custom']

            memory_share_level = _current_resource_pool_config.get(
                'memory_share_level').lower()
            if memory_share_level is not None and memory_share_level in SHARESINFO_LEVEL:
                if memory_share_level == 'custom':
                    memoryAllocation_share.level = memory_share_level
                    if _current_resource_pool_config.get('memory_shares'):
                        memoryAllocation_share.shares = _current_resource_pool_config.get(
                            'memory_shares')
                    else:
                        raise RuntimeError(
                            f"For MEMORY Allocation Custom Share Level, Value of Shares must be provided with parameter [memory_shares].")
                else:
                    memoryAllocation_share.level = memory_share_level
            else:
                raise RuntimeError(
                    f"MEMORY Allocation SHARE LEVEL Must be only {SHARESINFO_LEVEL}. Provided memory_share_level: {memory_share_level}")

            memoryAllocation_spec.shares = memoryAllocation_share

            resource_pool_spec.memoryAllocation = memoryAllocation_spec
            _current_resource_pool_obj.UpdateConfig(
                _current_resource_pool_name, resource_pool_spec)

            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: Edit Resource Pool: {_current_resource_pool_name} Completed for following config: {_current_resource_pool_config}", TASK_STATUS.COMPLETED)
        except Exception as e:
            _exception_msg = f"Failed: {_function_name} on Resource Pool: {_current_resource_pool_name} With Error/Exception: {str(e)}"
            exception_list.append(
                {_current_resource_pool_name: _exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} On Resource Pool:{exception_list}")


def delete_datacenter(parameters, session, **kwargs):
    # Delete Data Center
    _module_name = "VMOperation"
    _function_name = "delete_dc"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} Delete Data Center: {parameters}", {
              'task_id': task_id})
    operation_data_center_list = parameters.get('data_center_name')
    if isinstance(operation_data_center_list, str):
        operation_data_center_list = [operation_data_center_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: with PARAMETERS:{parameters}", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    exception_list = []

    for _current_data_center in operation_data_center_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Start {_function_name} Operation for Data Center: [{_current_data_center}]", TASK_STATUS.COMPLETED)
        try:
            _current_data_center_obj = vmware_commonoperations.get_obj(
                content, [vim.Datacenter], _current_data_center)

            task = _current_data_center_obj.Destroy_Task()
            vmware_commonoperations.async_tasks_wait(compute_client, [task])
            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: Delete Data Center: [{_current_data_center}] Completed.", TASK_STATUS.COMPLETED)
        except RuntimeError:
            _exception_msg = f"Failed With Error: No Such Data Center: [{_current_data_center}] found."
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.COMPLETED)
            exception_list.append({_current_data_center: _exception_msg})

        except Exception as e:
            _exception_msg = f"Failed: {_function_name} on Data Center: [{_current_data_center}] With Error/Exception: {str(e)}"
            exception_list.append(
                {_current_data_center: _exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)

    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} On Data Center:{exception_list}")


def delete_vswitch(parameters, session, **kwargs):
    # Delete vSwitch from ESXI HOST
    _module_name = "VMOperation"
    _function_name = "delete_vswitch"

    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} Delete vSwitch: {parameters}", {
              'task_id': task_id})
    esxi_host = parameters.get('esxi_host')
    operation_vswitch_list = parameters.get('vswitch_name')
    if isinstance(operation_vswitch_list, str):
        operation_vswitch_list = [operation_vswitch_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: with PARAMETERS:{parameters}", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    exception_list = []

    for _current_vswitch in operation_vswitch_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Start {_function_name} Operation for ESXI_HOST: {esxi_host} VSWITCH: [{_current_vswitch}]", TASK_STATUS.COMPLETED)
        try:

            _current_esxi_host_obj = vmware_commonoperations.get_obj(
                content, [vim.HostSystem], esxi_host)

            _current_esxi_host_obj.configManager.networkSystem.RemoveVirtualSwitch(
                _current_vswitch)

            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: Deleted vSwitch: [{_current_vswitch}] of ESXI_HOST: {esxi_host} Completed.", TASK_STATUS.COMPLETED)

        except RuntimeError:
            _exception_msg = f"Failed With Error: No Such ESXI_HOST: [{esxi_host}] found."
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.COMPLETED)
            exception_list.append({_current_vswitch: _exception_msg})

        except vim.fault.NotFound:
            _exception_msg = f"Failed With Error: No Such vSwitch: [{_current_vswitch}] found on  ESXI_HOST: [{esxi_host}]."
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.COMPLETED)
            exception_list.append({_current_vswitch: _exception_msg})

        except Exception as e:
            print(e)
            _exception_msg = f"Failed: {_function_name} on ESXI_HOST: {esxi_host} vSwitch: [{_current_vswitch}] With Error/Exception: {str(e)}"
            exception_list.append(
                {_current_vswitch: _exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)

    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} On vSwitch:{exception_list}")

            
def delete_folder(parameters, session, **kwargs):
    # Remove Folder from DC
    _module_name = "DCoperations"
    _function_name = "delete_folder"
    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} Remove Folder from DC: {parameters}", {
              'task_id': task_id})
    operation_folder_name_list = parameters.get('folder_name')
    if isinstance(operation_folder_name_list, str):
        operation_folder_name_list = [operation_folder_name_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: with PARAMETERS:{parameters}", TASK_STATUS.COMPLETED)

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    exception_list = []

    for _current_folder_name in operation_folder_name_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Start {_function_name} Operation for FOLDER_NAME: [{_current_folder_name}]", TASK_STATUS.COMPLETED)
        try:
            _current_dc_folder_obj = vmware_commonoperations.get_obj(
                content, [vim.Folder], _current_folder_name)
            task = _current_dc_folder_obj.Destroy_Task()
            vmware_commonoperations.async_tasks_wait(compute_client, [task])

            add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                          f"Success: Deleted folder_name: [{_current_folder_name}] Completed.", TASK_STATUS.COMPLETED)

        except RuntimeError:
            _exception_msg = f"Failed With Error: No Such folder_name: [{_current_folder_name}] found."
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.COMPLETED)
            exception_list.append({_current_folder_name: _exception_msg})

        except Exception as e:
            print(e)
            _exception_msg = f"Failed: {_function_name} on folder_name: [{_current_folder_name}] With Error/Exception: {str(e)}"
            exception_list.append(
                {_current_folder_name: _exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)

    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} On folder_name:{exception_list}")


def add_portgrp_vswitch(parameters, session, **kwargs):
    
    _module_name = "VSwitchOperation"
    _function_name = "add_portgrp_vswitch"
    
    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Operation:{parameters}", {
              'task_id': task_id})
    
    host = parameters.get('host')        
    vswitch_name = parameters.get('vswitch_name')    
    portgroup_name = parameters.get('portgroup_name')    
    vlan_id= parameters.get('vlan_id')
    
    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: {host}", TASK_STATUS.COMPLETED)   

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    
    add_audit_log(session, task_id, f"{_module_name}",
        f"{_function_name}", f"Start {_function_name} Host: [{host}]", TASK_STATUS.COMPLETED)
    try:

        vm_host=vmware_commonoperations.get_obj(content, [vim.HostSystem], host)
        portgroup_spec = vim.host.PortGroup.Specification()
        portgroup_spec.vswitchName = vswitch_name
        portgroup_spec.name = portgroup_name
        portgroup_spec.vlanId = int(vlan_id)
        network_policy = vim.host.NetworkPolicy()
        network_policy.security = vim.host.NetworkPolicy.SecurityPolicy()
        network_policy.security.allowPromiscuous = True
        network_policy.security.macChanges = False
        network_policy.security.forgedTransmits = False
        portgroup_spec.policy = network_policy
        
        vm_host.configManager.networkSystem.AddPortGroup(portgroup_spec)
        
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",f"Success: {_module_name} for host: {host}", TASK_STATUS.COMPLETED)
    except Exception as e:
        _exception_msg = f"Failed: {_function_name} on host: {host} With Error/Exception: {str(e)}"
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)


def del_portgrp_vswitch(parameters, session, **kwargs):
    
    _module_name = "VSwitchOperation"
    _function_name = "del_portgrp_vswitch"
    
    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} VMware Operation:{parameters}", {
              'task_id': task_id})
    
    host = parameters.get('host')            
    portgroup_name = parameters.get('portgroup_name')    

    
    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started on: {host} Portgroup : {portgroup_name}",TASK_STATUS.COMPLETED)   

    compute_client = get_vmware_client(parameters)
    content = compute_client.content
    
    
    add_audit_log(session, task_id, f"{_module_name}",
        f"{_function_name}", f"Start {_function_name} Host: [{host}] Portgroup : {portgroup_name}", TASK_STATUS.COMPLETED)
    try:

        vm_host=vmware_commonoperations.get_obj(content, [vim.HostSystem], host)
        vm_host.configManager.networkSystem.RemovePortGroup(portgroup_name)
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",f"Success: {_module_name} for Host: [{host}] Portgroup : {portgroup_name}", TASK_STATUS.COMPLETED)
    except Exception as e:
        _exception_msg = f"Failed: {_function_name} on host: {host} With Error/Exception: {str(e)}"
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)




