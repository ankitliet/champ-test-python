import json
import requests
import base64
from copy import deepcopy
from requests.models import PreparedRequest
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.state_response_insert import insert_state_response
from util.core.app.constants import TASK_STATUS
from util.core.app.models import APIConfig as APIConfigurations

from util.core.app.logger import get_logger_func
LOG = get_logger_func(__file__)



#GLOBALS
asset_map = {
    'htccloud': {
        'discover_type': {
            'UBUNTU': 'Ubuntu(Linux)',
            'CENTOS': 'CentOS(Linux)',
            'RHEL': 'RHEL',
            'SUSE': 'SUSE(Linux)',
            'WIN2012': 'Windows 2012 R2',
            'WIN2016': 'Windows 2016',
            'WIN2019': 'Windows 2019'
        },
        'discover_version': {
            '69': '6.9',
            '70': '7.0',
            '71': '7.1',
            '72': '7.2',
            '73': '7.3',
            '74': '7.4',
            '75': '7.5',
            '76': '7.6',
            '77': '7.7',
            '78': '7.8',
            '79': '7.9',
            '80': '8.0',
            '81': '8.1',
            '82': '8.2',
            '1804': '18.04',
            '2004': '20.04',
            '2012STD': '2012 R2 Standard',
            '2012DC': '2012 R2 Datacenter',
            '2016STD': '2016 Standard',
            '2016DC': '2016 Datacenter',
            '2019STD': '2019 Standard',
            '2019DC': '2019 Datacenter',
            '152': '15.2'
        }
    }
}




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

    

    
def fetch_apimeta(task_id: str, cloud_provider: str, source: str, task_name: str, session):
    meta = session._session_factory().query(
        APIConfigurations
    ).where(
        APIConfigurations.application_name.__eq__(
            source
        )
    ).where(
        APIConfigurations.task_name.__eq__(
            task_name
        )
    ).where(
        APIConfigurations.cloud_provider.__eq__(
            cloud_provider
        )
    ).one()
    LOG.debug(f"PostProvisiong[{source}] metainfo[{meta._asdict().__repr__()}]", {'task_id': task_id})
    if not meta.request_url:
        raise Exception("IPAM url is missing:%s" % task_name)
    return meta._asdict()



def hit(method: str, url: str, headers={}, data={}):
    LOG.debug("URL: %s, Payload:%s" % (url, data))
    data = {"encryptedText": base64.b64encode(json.dumps(data).encode()).decode()}
    if method == 'GET':
        resp = requests.get(url, headers=headers, verify=False)
    elif method == 'POST':
        resp = requests.post(url, headers=headers, data=json.dumps(data),
                             verify=False)
    elif method == 'PUT':
        resp = requests.put(url, headers=headers, data=json.dumps(data),
                            verify=False)
    return resp
        
        
        
def execute(func_name, parameters, session, **kwargs):
    if func_name == 'asset_management':
        return execute__asset_management(
            parameters=parameters, session=session, **kwargs
            
        )
    try:
        task_id = parameters.get('task_id')
        LOG.debug(f"{func_name}:{parameters}", {'task_id': task_id})
        apimeta = fetch_apimeta(
            task_id=task_id, 
            cloud_provider=parameters.get('cloud_provider'), 
            source=parameters.get('source'), 
            task_name=func_name,
            session=session
        )
        data = deepcopy(apimeta['request_parameters'])
        for key, value in apimeta['request_parameters_map'].items():
            tmp = deepcopy(parameters)
            for val in value:
                tmp = tmp[val]
            data[key] = tmp
        add_audit_log(
            session, task_id, "PostProvisiong", func_name, 
            json.dumps({
                'method': apimeta['method'], 'url': apimeta['request_url'], 'headers': apimeta.get('headers', {}), 
                'data': data
            }), 
            TASK_STATUS.COMPLETED
        )
        resp = hit(
            method=apimeta['method'],
            url=apimeta['request_url'],
            headers=apimeta.get('headers', {}),
            data=data
        )
        try:
            resp.raise_for_status()
            resp = resp.json()
            lctmp = {'resources': [resp]}
            add_state_response(session, task_id, f'{task_id}_{func_name}', json.dumps(lctmp))
        except Exception as excp:
            lctmp = {'resources': [resp.text]}
            add_state_response(session, task_id, f'{task_id}_{func_name}', json.dumps(lctmp))
            add_audit_log(
                session, task_id, "PostProvisiong", func_name, resp.text, TASK_STATUS.FAILED
            )
            raise excp
        for key, value in apimeta['response_parameters_map'].items():
            tmp = deepcopy(resp)
            for val in value:
                tmp = tmp[val]
            parameters[key] = tmp
        add_audit_log(
            session, task_id, "PostProvisiong", func_name, resp.__repr__(), TASK_STATUS.COMPLETED
        )
        return parameters
    except Exception as excp:
        add_audit_log(
            session, task_id, "PostProvisiong", func_name, excp.__repr__(), TASK_STATUS.FAILED
        )
        raise excp
        
        
        
def execute__asset_management(parameters, session, **kwargs):
    func_name = 'asset_management'
    try:
        task_id = parameters.get('task_id')
        LOG.debug(f"{func_name}:{parameters}", {'task_id': task_id})
        apimeta = fetch_apimeta(
            task_id=task_id, 
            cloud_provider=parameters.get('cloud_provider'), 
            source=parameters.get('source'), 
            task_name=func_name,
            session=session
        )
        data = deepcopy(apimeta['request_parameters'])
        for key, value in apimeta['request_parameters_map'].items():
            tmp = deepcopy(parameters)
            for val in value:
                tmp = tmp[val]
            data[key] = tmp
        # discover_type = parameters.get('discoverTech', 'NA')
        # discover_version = parameters.get('discoverVer', 'NA')
        # if parameters['cloud_provider'] == 'htccloud':
        #     template_name = parameters['template_name']
        #     for key in asset_map['htccloud']['discover_type'].keys():
        #         if template_name.find(key):
        #             discover_type = asset_map['htccloud']['discover_type'][key]
        #     for key in asset_map['htccloud']['discover_version'].keys():
        #         if template_name.find(key):
        #             discover_version = asset_map['htccloud']['discover_version'][key]
        data['discoverTech'] = parameters.get('discover_tech', 'NA')
        data['discoverVer'] = parameters.get('discover_ver', 'NA')
        add_audit_log(
            session, task_id, "PostProvisiong", func_name, 
            json.dumps({
                'method': apimeta['method'], 'url': apimeta['request_url'], 'headers': apimeta.get('headers', {}), 
                'data': data
            }), 
            TASK_STATUS.COMPLETED
        )
        resp = hit(
            method=apimeta['method'],
            url=apimeta['request_url'],
            headers=apimeta.get('headers', {}),
            data=data
        )
        try:
            resp.raise_for_status()
            resp = resp.json()
            lctmp = {'resources': [resp]}
            add_state_response(session, task_id, f'{task_id}_{func_name}', json.dumps(lctmp))
        except Exception as excp:
            lctmp = {'resources': [resp.text]}
            add_state_response(session, task_id, f'{task_id}_{func_name}', json.dumps(lctmp))
            add_audit_log(
                session, task_id, "PostProvisiong", func_name, resp.text, TASK_STATUS.FAILED
            )
            raise excp
        for key, value in apimeta['response_parameters_map'].items():
            tmp = deepcopy(resp)
            for val in value:
                tmp = tmp[val]
            parameters[key] = tmp
        add_audit_log(
            session, task_id, "PostProvisiong", func_name, resp.__repr__(), TASK_STATUS.COMPLETED
        )
        return parameters
    except Exception as excp:
        add_audit_log(
            session, task_id, "PostProvisiong", func_name, excp.__repr__(), TASK_STATUS.FAILED
        )
        raise excp