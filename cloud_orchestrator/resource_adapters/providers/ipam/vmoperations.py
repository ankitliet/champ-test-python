import json

import requests
from requests.models import PreparedRequest
req = PreparedRequest()
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from util.core.app.models import APIConfig as APIConfigurations

from util.core.app.logger import get_logger_func
LOG = get_logger_func(__file__)

parameters_map = {
    "vcenter_ip_address": "vsphere_server",
    "management_ip": "esxi_host",
    "port_group_name": "network_name",
    "gateway": "virtual_machine_gateway",
    "service_account": "vsphere_user",
    "__e__service_cred": "__e__vsphere_password",
    "datacenter_name": "dc_name"
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

def get_api_url(parameters, session, task_name):
    task_id = parameters.get('task_id')
    api_url_info = session._session_factory().query(
        APIConfigurations).where(
        APIConfigurations.application_name.__eq__(parameters.get('source'))).where(
        APIConfigurations.task_name.__eq__(task_name)).where(
        APIConfigurations.cloud_provider.__eq__(parameters.get('cloud_provider'))).one()

    LOG.debug("IPAM url info is:%s" % api_url_info.request_url,
                       {'task_id': task_id})
    if not api_url_info.request_url:
        raise Exception("IPAM url is missing:%s" % task_name)
    return api_url_info.request_url, api_url_info.credentials

def api_call(url, payload, headers = None, method="PUT"):
    LOG.debug("URL: %s, Payload:%s" % (url, payload))
    if method == "PUT":

        res = requests.put(url, data=json.dumps(payload), headers=headers)
    elif method == "GET":
        res = requests.get(url)
    else:
        raise Exception("Unsupported method")
    if res.status_code == 200:
        return res.json()
    else:
        raise Exception("API call %s failed. Message:%s" % (url, res.json()))

def get_eligible_base_host(parameters, session, **kwargs):
    # Get the eligible host
    task_id = parameters.get('task_id')
    LOG.debug("eligible_base_host:%s" % parameters, {'task_id': task_id})
    url, _ = get_api_url(parameters, session, 'elgible_base_host')
    is_os_ssd_disk = parameters.get('os_storage_disk', 0) and \
                     parameters.get('os_storage_disk').lower() == 'ssd'

    is_data_ssd_disk = parameters.get('data_disk_type', 0) and \
                       parameters.get('data_disk_type').lower() == 'ssd'

    payload = {
        "external_customer_id": parameters.get('cust_id'), # For testing
        "resource_type": parameters.get('resource_type'),
        "env_map_id": parameters.get('appenvmap_id'),
        "required_cpu": parameters.get('num_cpus'),
        "required_memory": parameters.get('memory'),
        "os_storage_size": parameters.get('os_storage_size'),
        "data_storage_size": parameters.get('data_storage_size'),
        "os_storage_type": parameters.get('os_storage_type', 'Local'),
        "is_os_ssd_disk": int(is_os_ssd_disk),
        "data_storage_type": parameters.get('data_storage_type', 'Local'),
        "is_data_ssd_disk": int(is_data_ssd_disk)
    }
    reqs = PreparedRequest()
    reqs.prepare_url(url, payload)
    url = reqs.url

    add_audit_log(session, task_id, "VmOperation",
                  "get_eligible_base_host:%s" % url,
                  "started", TASK_STATUS.COMPLETED)
    data = api_call(url, payload, method="GET")
    print(data)

    datastore_found = False
    if data.get('status') == "Success":
        details = data.get('details')
        if details:
            # from resource_adapters.providers.vmware.vmoperations import \
            #     get_host_details, validate_host_details
            # for host_detail in details:
            import random
            random_host = random.randint(0, len(details) - 1)
            for key, value in details[random_host].items():
                if key in parameters_map:
                    key = parameters_map[key]
                if key == "virtual_machine_gateway":
                    if isinstance(value, str):
                        value = [value]
                parameters[key] = value
                # host_details = get_host_details(parameters)
                # add_audit_log(session, task_id, "VmOperation",
                #               "get_eligible_base_host",
                #               "Host details:%s" % host_details, TASK_STATUS.COMPLETED)
                # datastore_name = validate_host_details(parameters, host_details)
                # if datastore_name:
                #     parameters['os_datastore_name'] = datastore_name
                #     parameters['data_datastore_name'] = datastore_name
                #     datastore_found = True
                #     break
            # if not datastore_found:
            #     add_audit_log(session, task_id, "VmOperation",
            #                   "get_eligible_base_host",
            #                   "Failed:%s" % data, TASK_STATUS.FAILED)
            #     raise Exception("Failed to found host with required capacity:%s" % data)

            # configure missing fields:
            if parameters.get('memory'):
                parameters['memory'] = int(parameters.get('memory')) * 1024

            if parameters.get('subnet') and len(parameters.get('subnet').split("/")) > 1:
                parameters['virtual_machine_network_mask'] = \
                    [parameters.get('subnet').split("/")[1]]
            print(parameters)
        else:
            add_audit_log(session, task_id, "VmOperation",
                          "get_eligible_base_host",
                          "Failed:%s" % data, TASK_STATUS.FAILED)
            raise Exception("Get host api failed to return the host details:%s" % data)
    else:
        add_audit_log(session, task_id, "VmOperation",
                      "get_eligible_base_host",
                      "Failed:%s" % data, TASK_STATUS.FAILED)
        raise Exception("Get host api failed to return the host details:%s" % data)
    add_audit_log(session, task_id, "VmOperation",
                  "get_eligible_base_host",
                  "Success:%s" % data, TASK_STATUS.COMPLETED)
    LOG.debug(json.dumps(parameters))

def reserve_ip(parameters, session, **kwargs):
    # Reserve the Ip
    task_id = parameters.get('task_id')
    LOG.debug("reserve_ip:%s" % parameters, {'task_id': task_id})
    url, credentials = get_api_url(parameters, session, 'reserve_ip')
    add_audit_log(session, task_id, "VmOperation", "reserve_ip:%s" % url,
                  "started", TASK_STATUS.COMPLETED)
    subnet = parameters.get('subnet')
    payload = {
        "subnet": subnet,
        "transaction_id": task_id
    }
    headers = {
        "credentials": credentials,
        'content-type': 'application/json'
    }
    url = url % (subnet.split("/")[0], subnet.split("/")[1])
    LOG.debug("URL is:%s" % url)
    data = api_call(url, payload, headers=headers)
    LOG.debug(data)
    if data.get('status') == "Success":
        details = data.get('details').get('data')
        parameters['virtual_machine_network_address'] = [details.get('IP')]
        add_audit_log(session, task_id, "VmOperation", "reserve_ip:%s" % data,
                      "Success", TASK_STATUS.COMPLETED)
    else:
        add_audit_log(session, task_id, "VmOperation",
                      "reserve_ip:%s" % data,
                      "Failed", TASK_STATUS.FAILED)
        raise Exception("Reserve IP api call failed:%s" % data)

def register_ip(parameters, session, **kwargs):
    # Register the Ip
    task_id = parameters.get('task_id')
    LOG.debug("register_ip:%s" % parameters, {'task_id': task_id})
    url, credentials = get_api_url(parameters, session, 'register_ip')
    add_audit_log(session, task_id, "VmOperation", "register_ip:%s" % url,
                  "started", TASK_STATUS.COMPLETED)
    headers = {
        "credentials": credentials,
        'content-type': 'application/json'
    }
    ip_address = parameters.get('virtual_machine_network_address')[0]
    payload = {
        "ip": ip_address,
        "transaction_id": task_id,
        "serial_number": parameters.get('uuid')[0]
    }
    url = url % (ip_address)
    LOG.debug("URL is:%s" % url)
    try:
        data = api_call(url, payload, headers=headers)
        LOG.debug(data)
    except Exception as ex:
        # If register ip api fails, call reserve ip once
        LOG.debug("Register IP exception:%s" % ex)
        reserve_ip(parameters, session)
        data = api_call(url, payload, headers=headers)

    if data.get('status') != "Success":
        LOG.debug("Register IP failed, retrigger reserve ip once")
        reserve_ip(parameters, session)
        data = api_call(url, payload, headers=headers)

    if data.get('status') == "Success":
        add_audit_log(session, task_id, "VmOperation", "register_ip:%s" % data,
                      "Success", TASK_STATUS.COMPLETED)
    else:
        add_audit_log(session, task_id, "VmOperation",
                      "register_ip:%s" % data,
                      "Failed", TASK_STATUS.FAILED)
        raise Exception("Register IP api call failed:%s" % data)

def unreserve_ip(parameters, session, **kwargs):
    # Un Reserve the Ip
    task_id = parameters.get('task_id')
    LOG.debug("unreserve_ip:%s" % parameters, {'task_id': task_id})
    if parameters.get('un_reserved'):
        LOG.debug("IP already un reserved:%s" % parameters, {'task_id': task_id})

    url, credentials = get_api_url(parameters, session, 'unreserve_ip')
    add_audit_log(session, task_id, "UnReserveIP", "unreserve_ip:%s" % url,
                  "started", TASK_STATUS.COMPLETED)
    headers = {
        "credentials": credentials,
        'content-type': 'application/json'
    }
    ip_address = parameters.get('virtual_machine_network_address')[0]
    payload = {
        "ip": ip_address,
        "transaction_id": task_id
    }
    url = url % (ip_address)
    LOG.debug("URL is:%s" % url)
    try:
        data = api_call(url, payload, headers=headers)
        LOG.debug(data)
        if data.get('status') == "Success":
            add_audit_log(session, task_id, "UnReserveIP", "unreserve_ip:%s" % data,
                          "Success", TASK_STATUS.COMPLETED)
            parameters["un_reserved"] = True
        else:
            add_audit_log(session, task_id, "UnReserveIP",
                          "unreserve_ip:%s" % data,
                          "Failed", TASK_STATUS.FAILED)
    except Exception as ex:
        add_audit_log(session, task_id, "UnReserveIP",
                      "unreserve_ip:%s" % str(ex),
                      "Failed", TASK_STATUS.FAILED)
