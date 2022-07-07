from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.state_response_insert import insert_state_response
from util.core.app.constants import TASK_STATUS
from resource_adapters.utils.storage_client import get_dell_isilon_client

import isi_sdk_8_2_1 as isilon_sdk
from isi_sdk_8_2_1.rest import ApiException
import json


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


def add_state_response(session, task_id, name, data):
    payload = {
        "name": name,
        "data": data
    }
    LOG.debug("Insert State Response:%s" % payload, {'task_id': task_id})
    insert_state_response(payload)

def create_nfs_export(parameters, session, **kwargs):
    # Create the NFS export for a file system
    _module_name = "StorageOperation"
    _function_name = "create_nfs_export"
    _ASYNC_REQ = True
    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} Create the NFS export for a file system: {parameters}", {
              'task_id': task_id})

    mount_path = parameters.get('mount_path')
    if mount_path is not None:
        if isinstance(mount_path, str):
            mount_path = [mount_path]
    else:
        parameters['mount_path'] = []
        mount_path = parameters.get('mount_path')

    private_ip = parameters.get('private_ip')
    if private_ip is not None:
        if isinstance(private_ip, str):
            private_ip = [private_ip]
    else:
        private_ip = None

    operation_nfs_export_info_list = parameters.get('nfs_export_info')
    if isinstance(operation_nfs_export_info_list, dict):
        operation_nfs_export_info_list = [operation_nfs_export_info_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: with PARAMETERS:{parameters}", TASK_STATUS.COMPLETED)

    api_client = get_dell_isilon_client(parameters)
    api_instance = isilon_sdk.ProtocolsApi(api_client)
    filesystem_api_instance = isilon_sdk.NamespaceApi(api_client)

    def path_exist(_ifs_path):
        PATH_EXIST = False
        if _ifs_path[0] == '/':
            _ifs_path = _ifs_path[1:]
        try:
            path_metadata = filesystem_api_instance.get_directory_metadata(
                directory_metadata_path=_ifs_path, metadata=True, async_req=_ASYNC_REQ)
            path_metadata = path_metadata.get().to_dict()
            path_metadata = path_metadata.get('attrs')
            if path_metadata is None:
                PATH_EXIST = False
            else:
                PATH_EXIST = True
        except Exception as e:
            pass
        LOG.debug(f"PATH_EXIST: FILE SYSTEM Path: [{_ifs_path}] Status: {PATH_EXIST}.")
        return PATH_EXIST

    def create_path(_ifs_path):
        if _ifs_path[0] == '/':
            _ifs_path = _ifs_path[1:]
        directory_path = _ifs_path
        x_isi_ifs_target_type = 'container'
        x_isi_ifs_access_control = '7777'
        recursive = True
        overwrite = True
        try:
            create_directory_api_response = filesystem_api_instance.create_directory(
                directory_path, x_isi_ifs_target_type, x_isi_ifs_access_control=x_isi_ifs_access_control, recursive=recursive, overwrite=overwrite,async_req=_ASYNC_REQ)
            create_directory_api_response.wait()
            if create_directory_api_response.successful():
                LOG.debug(f"Created FILE SYSTEM Path: [{directory_path}].")
            else:
                raise RuntimeError(create_directory_api_response.get())
        except ApiException as e:
            raise RuntimeError(
                f"Exception While Creating Path: {directory_path} with Error: {str(e)}")

    exception_list = []

    for _current_nfs_export_info in operation_nfs_export_info_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Start {_function_name} Operation for NFS export: [{_current_nfs_export_info}]", TASK_STATUS.COMPLETED)

        try:
            paths = _current_nfs_export_info.get('paths')
            mount_path.extend(paths)
            if parameters.get('software_installation_config'):
                parameters['software_installation_config']['mount_path'] = mount_path
            else:
                parameters['software_installation_config'] = {}
                parameters['software_installation_config']['mount_path'] = mount_path
            for ifs_path in paths:
                add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                f"Checking for {_function_name} Operation PATH_EXIST Path:[{ifs_path}]", TASK_STATUS.COMPLETED)
                check_path_exist = path_exist(ifs_path)
                if not check_path_exist:
                    create_path(ifs_path)
                    add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                f"Start {_function_name} Operation for NFS export: [{_current_nfs_export_info} Created FILE SYSTEM Path:[{ifs_path}]", TASK_STATUS.COMPLETED)
                else:
                    add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                                f"Start {_function_name} Operation for NFS export: [{_current_nfs_export_info} FILE SYSTEM Path:[{ifs_path}] Already Exists.", TASK_STATUS.COMPLETED)
        
            root_clients = _current_nfs_export_info.get('root_clients')
            read_write_clients = _current_nfs_export_info.get(
                'read_write_clients')
            if isinstance(private_ip, list):
                if root_clients is not None:
                    _current_nfs_export_info['root_clients'].extend(private_ip)
                else:
                    _current_nfs_export_info['root_clients'] = private_ip
                if read_write_clients is not None:
                    _current_nfs_export_info['read_write_clients'].extend(
                        private_ip)
                else:
                    _current_nfs_export_info['read_write_clients'] = private_ip

            nfs_export_spec = isilon_sdk.NfsExportCreateParams(
                **_current_nfs_export_info)
            _force = False
            _ignore_unresolvable_hosts = True
            _ignore_conflicts = False
            _ignore_bad_paths = False
            _ignore_bad_auth = True

            api_response = api_instance.create_nfs_export(nfs_export=nfs_export_spec, async_req=_ASYNC_REQ, force=_force, ignore_unresolvable_hosts=_ignore_unresolvable_hosts,
                                                          ignore_conflicts=_ignore_conflicts, ignore_bad_paths=_ignore_bad_paths, ignore_bad_auth=_ignore_bad_auth)
            api_response.wait()
            if api_response.successful():
                name_resp = f"{task_id}_{_function_name}"
                data = {'task': _function_name}
                _current_nfs_export_id = api_response.get().id
                nfs_export_info = api_instance.get_nfs_export(
                    nfs_export_id=_current_nfs_export_id, async_req=_ASYNC_REQ)
                nfs_export_info = nfs_export_info.get()
                data['resources'] = [nfs_export_info.exports[0].to_dict()]
                add_state_response(
                    session, task_id, name_resp, json.dumps(data))
                add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                              f"Success: Created the NFS export for a file system: [{_current_nfs_export_info}] with NFS Export ID: {_current_nfs_export_id} Completed.", TASK_STATUS.COMPLETED)
            else:
                raise RuntimeError(api_response.get())
        except ApiException as api_ex:
            _api_exception_msg = f"Failed: {_function_name} for NFS export info: [{_current_nfs_export_info}] With REST API Error/Exception: {str(api_ex)}"
            exception_list.append(_api_exception_msg)
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _api_exception_msg, TASK_STATUS.FAILED)

        except Exception as ex:
            _exception_msg = f"Failed: {_function_name} for NFS export info: [{_current_nfs_export_info}] With Python Error/Exception: {str(ex)}"
            exception_list.append(_exception_msg)
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} for NFS:{exception_list}")



def delete_nfs_export(parameters, session, **kwargs):
    # Delete the NFS export
    _module_name = "StorageOperation"
    _function_name = "delete_nfs_export"
    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} Delete the NFS export: {parameters}", {
              'task_id': task_id})

    operation_nfs_export_id_list = parameters.get('nfs_export_id')
    if isinstance(operation_nfs_export_id_list, int):
        operation_nfs_export_id_list = [operation_nfs_export_id_list]

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: with PARAMETERS:{parameters}", TASK_STATUS.COMPLETED)

    api_client = get_dell_isilon_client(parameters)
    api_instance = isilon_sdk.ProtocolsApi(api_client)

    exception_list = []

    for _current_nfs_export_id in operation_nfs_export_id_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Start {_function_name} Operation for NFS export: [{_current_nfs_export_id}]", TASK_STATUS.COMPLETED)

        try:
            _async_req = True
            api_response = api_instance.delete_nfs_export(
                _current_nfs_export_id, async_req=_async_req)
            api_response.wait()
            if api_response.successful():
                add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                              f"Success: Deleted the NFS export ID: [{_current_nfs_export_id}] Completed.", TASK_STATUS.COMPLETED)
            else:
                raise RuntimeError(api_response.get())

        except ApiException as api_ex:
            _api_exception_msg = f"Failed: {_function_name} for NFS export info: [{_current_nfs_export_id}] With REST API Error/Exception: {str(api_ex)}"
            exception_list.append(
                {_current_nfs_export_id: _api_exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _api_exception_msg, TASK_STATUS.FAILED)

        except Exception as ex:
            _exception_msg = f"Failed: {_function_name} for NFS export info: [{_current_nfs_export_id}] With Python Error/Exception: {str(ex)}"
            exception_list.append(
                {_current_nfs_export_id: _exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)

    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} for NFS:{exception_list}")


def modify_nfs_export(parameters, session, **kwargs):
    # Modify attributes of NFS export
    _module_name = "StorageOperation"
    _function_name = "modify_nfs_export"
    task_id = parameters.get('task_id')
    LOG.debug(f"{_module_name}:{_function_name} Modify attributes of NFS export: {parameters}", {
              'task_id': task_id})

    operation_nfs_export_id_list = parameters.get('nfs_export_id')
    if isinstance(operation_nfs_export_id_list, int):
        operation_nfs_export_id_list = [operation_nfs_export_id_list]

    modified_nfs_export_info = parameters.get('modified_nfs_export_info')
    if modified_nfs_export_info is None:
        modified_nfs_export_info={}

    mount_path = parameters.get('mount_path')
    if mount_path is not None:
        if isinstance(mount_path, str):
            mount_path = [mount_path]
    else:
        parameters['mount_path']=[]
        mount_path = parameters.get('mount_path')

    private_ip = parameters.get('private_ip')
    if private_ip is not None:
        if isinstance(private_ip, str):
            private_ip = [private_ip]
    else:
        private_ip = None

    add_audit_log(session, task_id, f"{_module_name}",
                  f"{_function_name}", f"Started: with PARAMETERS:{parameters}", TASK_STATUS.COMPLETED)

    api_client = get_dell_isilon_client(parameters)
    api_instance = isilon_sdk.ProtocolsApi(api_client)

    exception_list = []

    for _current_nfs_export_id in operation_nfs_export_id_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Start {_function_name} Operation for NFS EXPORT ID: [{_current_nfs_export_id}]", TASK_STATUS.COMPLETED)

        try:
            _async_req = True
            _force = True
            _ignore_unresolvable_hosts = True
            _ignore_conflicts = True
            _ignore_bad_paths = True
            _ignore_bad_auth = True

            nfs_export_info = api_instance.get_nfs_export(
                nfs_export_id=_current_nfs_export_id, async_req=_async_req)
            nfs_export_info = nfs_export_info.get()
            nfs_export_info = nfs_export_info.exports[0].to_dict()

            paths = nfs_export_info.get('paths')
            mount_path.extend(paths)
            if isinstance(private_ip, list):
                if modified_nfs_export_info.get('root_clients') is not None:
                    modified_nfs_export_info['root_clients'].extend(private_ip)
                else:
                    modified_nfs_export_info['root_clients'] = private_ip
                if modified_nfs_export_info.get('read_write_clients') is not None:
                    modified_nfs_export_info['read_write_clients'].extend(
                        private_ip)
                else:
                    modified_nfs_export_info['read_write_clients'] = private_ip
            root_clients = nfs_export_info.get('root_clients')
            read_write_clients = nfs_export_info.get(
                'read_write_clients')
            if root_clients is not None:
                root_clients.extend(
                    modified_nfs_export_info.get('root_clients'))
                modified_nfs_export_info['root_clients'] = root_clients
            if read_write_clients is not None:
                read_write_clients.extend(
                    modified_nfs_export_info.get('read_write_clients'))
                modified_nfs_export_info['read_write_clients'] = read_write_clients

            nfs_export_spec = isilon_sdk.NfsExport(**modified_nfs_export_info)
            api_response = api_instance.update_nfs_export(nfs_export=nfs_export_spec, nfs_export_id=_current_nfs_export_id,
                                                          async_req=_async_req, force=_force, ignore_unresolvable_hosts=_ignore_unresolvable_hosts,
                                                          ignore_conflicts=_ignore_conflicts, ignore_bad_paths=_ignore_bad_paths, ignore_bad_auth=_ignore_bad_auth)
            api_response.wait()
            if api_response.successful():
                name_resp = f"{task_id}_{_function_name}"
                data = {'task': _function_name}

                data['resources'] = [nfs_export_info]
                add_state_response(
                    session, task_id, name_resp, json.dumps(data))
                add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                              f"Success: Modified the NFS export ID: [{_current_nfs_export_id}] \
                                  with New attributes: [{modified_nfs_export_info}] Completed.", TASK_STATUS.COMPLETED)
            else:
                raise RuntimeError(api_response.get())

        except ApiException as api_ex:
            _api_exception_msg = f"Failed: {_function_name} for NFS EXPORT ID: [{_current_nfs_export_id}] with New attributes: [{modified_nfs_export_info}]. \
                \n Got REST API Error/Exception: {str(api_ex)}"
            exception_list.append({_current_nfs_export_id: _api_exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _api_exception_msg, TASK_STATUS.FAILED)

        except Exception as ex:
            _exception_msg = f"Failed: {_function_name} for NFS EXPORT ID: [{_current_nfs_export_id}] with New attributes: [{modified_nfs_export_info}]. \
                \n Got Python Error/Exception: {str(ex)}"
            exception_list.append({_current_nfs_export_id: _exception_msg})
            add_audit_log(session, task_id, f"{_module_name}",
                          f"{_function_name}", _exception_msg, TASK_STATUS.FAILED)
    if exception_list:
        add_audit_log(session, task_id, f"{_module_name}", f"{_function_name}",
                      f"Failed With Error: {exception_list}", TASK_STATUS.FAILED)
        raise Exception(
            f"Failed To Perform {_module_name}:{_function_name} for NFS Export:{exception_list}")