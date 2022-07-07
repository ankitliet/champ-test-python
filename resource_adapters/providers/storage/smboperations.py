import isi_sdk_8_2_1
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.state_response_insert import insert_state_response
from util.core.app.constants import TASK_STATUS
from resource_adapters.utils.storage_client import get_dell_isilon_client
import json
from copy import deepcopy


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


def add_state_response(session,task_id,name,data):
    payload = {
        "name": name,
        "data": data
    }
    LOG.debug("Insert State Response:%s" % payload, {'task_id': task_id})
    insert_state_response(payload)


def create_smb_share(parameters_org, session, **kwargs):
    parameters = deepcopy(parameters_org)
    task_id = parameters.get('task_id')
    mount_paths = []
    LOG.debug("create_smb_share Storage op:%s" % parameters, {'task_id': task_id})
    try:
        configuration = get_dell_isilon_client(parameters)
        api_instance = isi_sdk_8_2_1.ProtocolsApi(configuration)
    except Exception as ex:
        raise Exception('Cannot Create Storage client ({})'.format(str(ex)))

    smb_info = parameters.get('smb_info')
    ops_failed = []
    if isinstance(smb_info, dict):
        smb_info = [smb_info]
    for smb in smb_info:
        if 'name' not in smb or smb.get('name') is None:
            raise Exception('name not provided in Payload')
        name = smb.get('name')
        
        
        if 'zone' not in smb or smb.get('zone') is None:
            raise Exception('Zone not provided in Payload')
        zone = smb.get('zone')
        del smb['zone']
        
        if 'permissions' in smb:
            for perm in smb['permissions']:
                if not isinstance(perm,dict):
                    raise Exception('Invalid permissions Value provided ,dictionary required')

                if 'trustee' in perm:
                    if isinstance(perm['trustee'],dict):
                        perm['trustee'] = isi_sdk_8_2_1.AuthAccessAccessItemFileGroup(**perm['trustee'])
                    else:
                        raise Exception('Invalid trustee Value provided({})'.format(str(ex)))

                perm = isi_sdk_8_2_1.SmbSharePermission(**perm)
        
        if 'run_as_root' in smb:
            for perm in smb['run_as_root']:
                if not isinstance(perm,dict):
                    raise Exception('Invalid run_as_root Value provided,dictionary required')
                perm = isi_sdk_8_2_1.AuthAccessAccessItemFileGroup(**perm)
                


        add_audit_log(session, task_id, "StorageOperation", "create_smb_share:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            smb_share = isi_sdk_8_2_1.SmbShareCreateParams(**smb)
            ext = False
            try:
                api_resp = api_instance.get_smb_share(name,zone=zone)
                ext = True
            except Exception as ex:
                pass

            if ext:
                raise Exception('Smb {} already Exists'.format(name))

            api_response = api_instance.create_smb_share(smb_share, zone=zone,async_req=True)
            
            mount_paths.append(smb['path'])


            api_response.wait()
            if api_response.successful():
                add_audit_log(session, task_id, "StorageOperation", "create_smb_share:%s" % name,
                    "Success", TASK_STATUS.COMPLETED)
            
            data = {'task':'create_smb_share'}
            data['resources'] = []
            api_resp = api_instance.get_smb_share(name,zone=zone)
            data['resources'] = [api_resp.shares[0].to_dict()]
            name_resp = task_id + '_' + 'create_smb_share'
            add_state_response(session,task_id,name_resp,json.dumps(data))
            add_audit_log(session, task_id, "StorageOperation", "create_smb_share:%s" % name,
                        "Add Resource to Response", TASK_STATUS.COMPLETED)
            
        except Exception as ex:
            add_audit_log(session, task_id, "StorageOperation", "create_smb_share:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)
            continue
        
    parameters_org['mount_paths'] = mount_paths
    if ops_failed:
        add_audit_log(session, task_id, "StorageOperation", "create_smb_share",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))



def delete_smb_share(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_smb_share Storage op:%s" % parameters, {'task_id': task_id})
    try:
        configuration = get_dell_isilon_client(parameters)
        api_instance = isi_sdk_8_2_1.ProtocolsApi(configuration)
    except Exception as ex:
        raise Exception('Cannot Create Storage client ({})'.format(str(ex)))

    smb_info = parameters.get('smb_info')
    ops_failed = []
    if isinstance(smb_info, dict):
        smb_info = [smb_info]
    for smb in smb_info:
        if 'smb_id' not in smb or smb.get('smb_id') is None:
            raise Exception('smb_id not provided in Payload')
        name = smb.get('smb_id')
        
        if 'zone' not in smb or smb.get('zone') is None:
            raise Exception('Zone not provided in Payload')
        zone = smb.get('zone')
        
        
        add_audit_log(session, task_id, "StorageOperation", "delete_smb_share:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            api_response = api_instance.delete_smb_share(name, zone=zone)
            add_audit_log(session, task_id, "StorageOperation", "delete_smb_share:%s" % name,
                    "Success", TASK_STATUS.COMPLETED)

        except Exception as ex:
            add_audit_log(session, task_id, "StorageOperation", "delete_smb_share:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)
            continue
        
        add_audit_log(session, task_id, "StorageOperation", "delete_smb_share:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "StorageOperation", "delete_smb_share",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def modify_smb_share(parameters_org, session, **kwargs):
    parameters = deepcopy(parameters_org)
    task_id = parameters.get('task_id')
    mount_paths = []
    LOG.debug("modify_smb_share Storage op:%s" % parameters, {'task_id': task_id})
    try:
        configuration = get_dell_isilon_client(parameters)
        api_instance = isi_sdk_8_2_1.ProtocolsApi(configuration)
    except Exception as ex:
        raise Exception('Cannot Create Storage client ({})'.format(str(ex)))

    smb_info = parameters.get('smb_info')
    ops_failed = []
    if isinstance(smb_info, dict):
        smb_info = [smb_info]
    for smb in smb_info:
        if 'name' not in smb or smb.get('name') is None:
            raise Exception('name not provided in Payload')
        name = smb.get('name')
        
        if 'zone' not in smb or smb.get('zone') is None:
            raise Exception('Zone not provided in Payload')
        zone = smb.get('zone')
        del smb['zone']
        
        if 'permissions' in smb:
            for perm in smb['permissions']:
                if not isinstance(perm,dict):
                    raise Exception('Invalid permissions Value provided ,dictionary required')

                if 'trustee' in perm:
                    if isinstance(perm['trustee'],dict):
                        perm['trustee'] = isi_sdk_8_2_1.AuthAccessAccessItemFileGroup(**perm['trustee'])
                    else:
                        raise Exception('Invalid trustee Value provided({})'.format(str(ex)))

                perm = isi_sdk_8_2_1.SmbSharePermission(**perm)
        
        if 'run_as_root' in smb:
            for perm in smb['run_as_root']:
                if not isinstance(perm,dict):
                    raise Exception('Invalid run_as_root Value provided,dictionary required')
                perm = isi_sdk_8_2_1.AuthAccessAccessItemFileGroup(**perm)
                


        add_audit_log(session, task_id, "StorageOperation", "modify_smb_share:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            smb_share = isi_sdk_8_2_1.SmbShare(**smb)
            
            api_response = api_instance.update_smb_share(smb_share,name, zone=zone)
            
            add_audit_log(session, task_id, "StorageOperation", "modify_smb_share:%s" % name,
                "Success", TASK_STATUS.COMPLETED)
            
            data = {'task':'modify_smb_share'}
            data['resources'] = []
            api_resp = api_instance.get_smb_share(name,zone=zone)
            mount_paths.append(api_resp.shares[0].path)
            data['resources'] = [api_resp.shares[0].to_dict()]
            name_resp = task_id + '_' + 'modify_smb_share'
            add_state_response(session,task_id,name_resp,json.dumps(data))
            add_audit_log(session, task_id, "StorageOperation", "modify_smb_share:%s" % name,
                        "Add Resource to Response", TASK_STATUS.COMPLETED)
            
        except Exception as ex:
            add_audit_log(session, task_id, "StorageOperation", "modify_smb_share:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)
            continue
        
    parameters_org['mount_paths'] = mount_paths
    if ops_failed:
        add_audit_log(session, task_id, "StorageOperation", "modify_smb_share",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def create_quotas(parameters, session, **kwargs):
    parameters = deepcopy(parameters)
    task_id = parameters.get('task_id')
    LOG.debug("create_quotas Storage op:%s" % parameters, {'task_id': task_id})
    try:
        configuration = get_dell_isilon_client(parameters)
        api_instance = isi_sdk_8_2_1.QuotaApi(configuration)
    except Exception as ex:
        raise Exception('Cannot Create Storage client ({})'.format(str(ex)))

    quota_info = parameters.get('quota_info')
    ops_failed = []
    if isinstance(quota_info, dict):
        quota_info = [quota_info]
    for smb in quota_info:
        if 'path' not in smb or smb.get('path') is None:
            raise Exception('Path not provided in Payload')
        name = smb.get('path')
        
        if 'zone' not in smb or smb.get('zone') is None:
            raise Exception('Zone not provided in Payload')
        zone = smb.get('zone')
        del smb['zone']
        
        if 'thresholds' in smb:
            perm = smb['thresholds']
            if not isinstance(perm,dict):
                raise Exception('Invalid thresholds Value provided ,dictionary required')

            smb['thresholds'] = isi_sdk_8_2_1.QuotaQuotaThresholds(**perm)
        
        if 'persona' in smb:
            perm = smb['persona']
            if not isinstance(perm,dict):
                raise Exception('Invalid persona Value provided,dictionary required')
            smb['persona'] = isi_sdk_8_2_1.AuthAccessAccessItemFileGroup(**perm)
                


        add_audit_log(session, task_id, "StorageOperation", "create_quotas:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            quota_quota = isi_sdk_8_2_1.QuotaQuotaCreateParams(**smb)
            api_response = api_instance.create_quota_quota(quota_quota,zone = zone)
            add_audit_log(session, task_id, "StorageOperation", "create_quotas:%s" % name,
                "Success", TASK_STATUS.COMPLETED)
            
            quota_id = api_response.id
            data = {'task':'create_quotas'}
            data['resources'] = []
            api_resp = api_instance.get_quota_quota(quota_id,zone=zone,resolve_names = True)
            data['resources'] = [api_resp.quotas[0].to_dict()]
            name_resp = task_id + '_' + 'create_quotas'
            add_state_response(session,task_id,name_resp,json.dumps(data))
            add_audit_log(session, task_id, "StorageOperation", "create_quotas:%s" % name,
                        "Add Resource to Response", TASK_STATUS.COMPLETED)
            
        except Exception as ex:
            add_audit_log(session, task_id, "StorageOperation", "create_quotas:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)
            continue
        
        
    if ops_failed:
        add_audit_log(session, task_id, "StorageOperation", "create_quotas",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))

def delete_quotas(parameters, session, **kwargs):
    parameters = deepcopy(parameters)
    task_id = parameters.get('task_id')
    LOG.debug("delete_quotas Storage op:%s" % parameters, {'task_id': task_id})
    try:
        configuration = get_dell_isilon_client(parameters)
        api_instance = isi_sdk_8_2_1.QuotaApi(configuration)
    except Exception as ex:
        raise Exception('Cannot Create Storage client ({})'.format(str(ex)))

    quota_paths = parameters.get('quota_paths')
    ops_failed = []
    if isinstance(quota_paths, dict):
        quota_paths = [quota_paths]
    for name in quota_paths:
        add_audit_log(session, task_id, "StorageOperation", "delete_quotas:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            
            api_response = api_instance.list_quota_quotas()
            quota_list = api_response.quotas
            ext = True
            for q in quota_list:
                if q.path == name:
                    api_resp = api_instance.delete_quota_quota(q.id)
                    ext = False
            if ext:
                raise Exception('No quota for path {} exists'.format(name))
            add_audit_log(session, task_id, "StorageOperation", "delete_quotas:%s" % name,
                "Success", TASK_STATUS.COMPLETED)
            
            
        except Exception as ex:
            add_audit_log(session, task_id, "StorageOperation", "delete_quotas:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)
            continue
        
        
    if ops_failed:
        add_audit_log(session, task_id, "StorageOperation", "delete_quotas",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))

def modify_quotas(parameters, session, **kwargs):
    parameters = deepcopy(parameters)
    task_id = parameters.get('task_id')
    LOG.debug("modify_quotas Storage op:%s" % parameters, {'task_id': task_id})
    try:
        configuration = get_dell_isilon_client(parameters)
        api_instance = isi_sdk_8_2_1.QuotaApi(configuration)
    except Exception as ex:
        raise Exception('Cannot Create Storage client ({})'.format(str(ex)))

    quota_info = parameters.get('quota_info')
    ops_failed = []
    if isinstance(quota_info, dict):
        quota_info = [quota_info]
    for smb in quota_info:
        if 'path' not in smb or smb.get('path') is None:
            raise Exception('Path not provided in Payload')
        name = smb.get('path')
        del smb['path']
        
        
        if 'zone' not in smb or smb.get('zone') is None:
            raise Exception('Zone not provided in Payload')
        zone = smb.get('zone')
        del smb['zone']
        
        
        if 'thresholds' in smb:
            perm = smb['thresholds']
            if not isinstance(perm,dict):
                raise Exception('Invalid thresholds Value provided ,dictionary required')

            smb['thresholds'] = isi_sdk_8_2_1.QuotaQuotaThresholds(**perm)
        
        if 'persona' in smb:
            perm = smb['persona']
            if not isinstance(perm,dict):
                raise Exception('Invalid persona Value provided,dictionary required')
            smb['persona'] = isi_sdk_8_2_1.AuthAccessAccessItemFileGroup(**perm)
                


        add_audit_log(session, task_id, "StorageOperation", "modify_quotas:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            quota_quota = isi_sdk_8_2_1.QuotaQuota(**smb)
            quotas = api_instance.list_quota_quotas()
            quota_id = None
            for q in quotas.quotas:
                if q.path == name:
                    quota_id = q.id
                    break
            if quota_id is None:
                raise Exception('No quota for the path {} found'.format(name))
            api_response = api_instance.update_quota_quota(quota_quota,quota_id)
            add_audit_log(session, task_id, "StorageOperation", "modify_quotas:%s" % name,
                "Success", TASK_STATUS.COMPLETED)
            
            #quota_id = api_response.id
            data = {'task':'modify_quotas'}
            data['resources'] = []
            api_resp = api_instance.get_quota_quota(quota_id,zone=zone,resolve_names = True)
            data['resources'] = [api_resp.quotas[0].to_dict()]
            name_resp = task_id + '_' + 'modify_quotas'
            add_state_response(session,task_id,name_resp,json.dumps(data))
            add_audit_log(session, task_id, "StorageOperation", "modify_quotas:%s" % name,
                        "Add Resource to Response", TASK_STATUS.COMPLETED)
            
        except Exception as ex:
            add_audit_log(session, task_id, "StorageOperation", "modify_quotas:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)
            continue
        
        
    if ops_failed:
        add_audit_log(session, task_id, "StorageOperation", "modify_quotas",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))
