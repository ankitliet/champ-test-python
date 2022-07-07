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

def delete_public_ip(parameters, session, **kwargs):
    # Delete public ip
    task_id = parameters.get('task_id')
    LOG.debug("delete_public_ip:%s" % parameters,
              {'task_id': task_id})
    address_client = get_gcp_address_client(parameters)
    op_client = get_gcp_op_client(parameters)
    add_audit_log(session, task_id, "NetworkOperations", "delete_public_ip",
                  "started", TASK_STATUS.COMPLETED)
    try:
        ip_config_info = parameters.get('ip_config_info')
    except Exception as ex:
        raise Exception("Ip configuration is missing:%s" % str(ex))
    ips_deleted = []
    ips_failed = []
    if ip_config_info:
        for ip_name in ip_config_info:
            try:
                LOG.debug("IP Name is:%s" % ip_name, {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_public_ip:%s" % ip_name,
                              "started", TASK_STATUS.COMPLETED)
                op = address_client.delete(project=parameters.get('gcp_project'),
                                                region=parameters.get('location'),
                                                address=ip_name)
                while op.status != compute_v1.Operation.Status.DONE:
                    op = op_client.wait(
                        operation=op.name, zone=parameters.get('zone'),
                        project=parameters.get('gcp_project'))
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_public_ip:%s" % ip_name,
                              "Success", TASK_STATUS.COMPLETED)
                ips_deleted.append(ip_name)
            except Exception as ex:
                ips_failed.append(ip_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_public_ip:%s" % ip_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "delete_public_ip Ips deleted:%s, Ips failed:%s" %
                      (ips_deleted, ips_failed), "Success", TASK_STATUS.COMPLETED)
        if ips_failed:
            add_audit_log(session, task_id, "NetworkOperations", "delete_public_ip",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(ips_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "delete_public_ip",
                      "No IP information in the request", TASK_STATUS.COMPLETED)

def delete_vnet(parameters, session, **kwargs):
    # Delete vnet
    task_id = parameters.get('task_id')
    LOG.debug("delete_vnet:%s" % parameters, {'task_id': task_id})
    network_client = get_gcp_network_client(parameters)
    wait_client = get_gcp_wait_client_global(parameters)
    add_audit_log(session, task_id, "NetworkOperations", "delete_vnet",
                  "started", TASK_STATUS.COMPLETED)
    try:
        vnet_config_info = parameters.get('vnet_config_info')
    except Exception as ex:
        raise Exception("Vnet configuration is missing:%s" % str(ex))
    ips_deleted = []
    ips_failed = []
    if vnet_config_info:
        for vnet_name in vnet_config_info:
            try:
                LOG.debug("IP Name is:%s" % vnet_name, {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_vnet:%s" % vnet_name,
                              "started", TASK_STATUS.COMPLETED)
                op = network_client.delete(project=parameters.get('gcp_project'),
                                           network=vnet_name)
                while op.status != compute_v1.Operation.Status.DONE:
                    op = wait_client.wait(operation=op.name,
                        project=parameters.get('gcp_project'))
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_vnet:%s" % vnet_name,
                              "Success", TASK_STATUS.COMPLETED)
                ips_deleted.append(vnet_name)
            except Exception as ex:
                ips_failed.append(vnet_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_vnet:%s" % vnet_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "delete_vnet Vnet deleted:%s, Vnet failed:%s" %
                      (ips_deleted, ips_failed), "Success", TASK_STATUS.COMPLETED)
        if ips_failed:
            add_audit_log(session, task_id, "NetworkOperations", "delete_vnet",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(ips_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "delete_public_ip",
                      "No Vnet information in the request", TASK_STATUS.COMPLETED)

def delete_subnet(parameters, session, **kwargs):
    # Delete SubNet
    task_id = parameters.get('task_id')
    LOG.debug("delete_subnet:%s" % parameters,
              {'task_id': task_id})
    subnet_client = get_gcp_subnet_client(parameters)
    wait_client_reg = get_gcp_wait_client_regional(parameters)
    add_audit_log(session, task_id, "NetworkOperations", "delete_subnet",
                  "started", TASK_STATUS.COMPLETED)
    try:
        subnet_config_info = parameters.get('subnet_config_info')
    except Exception as ex:
        raise Exception("SubNet configuration is missing:%s" % str(ex))
    ips_deleted = []
    ips_failed = []
    if subnet_config_info:
        for subnet_name in subnet_config_info:
            try:
                LOG.debug("IP Name is:%s" % subnet_name, {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_subnet:%s" % subnet_name,
                              "started", TASK_STATUS.COMPLETED)
                op = subnet_client.delete(project=parameters.get('gcp_project'),
                                          region=parameters.get('location'),
                                          subnetwork=subnet_name)
                while op.status != compute_v1.Operation.Status.DONE:
                    op = wait_client_reg.wait(operation=op.name,
                        project=parameters.get('gcp_project'),
                        region=parameters.get('location'))
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_subnet:%s" % subnet_name,
                              "Success", TASK_STATUS.COMPLETED)
                ips_deleted.append(subnet_name)
            except Exception as ex:
                ips_failed.append(subnet_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_subnet:%s" % subnet_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                           "delete_subnet SubNet deleted:%s, SubNet failed:%s" %
                           (ips_deleted, ips_failed),
                           "Success", TASK_STATUS.COMPLETED)
        if ips_failed:
            add_audit_log(session, task_id, "NetworkOperations", "delete_subnet",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(ips_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "delete_public_ip",
                      "No Subnet information in the request",
                      TASK_STATUS.COMPLETED)

def delete_firewall_rules(parameters, session, **kwargs):
    # Delete public ip
    task_id = parameters.get('task_id')
    LOG.debug("delete_firewall_rule:%s" % parameters,
              {'task_id': task_id})
    firewall_client = get_gcp_firewall_client(parameters)
    op_client = get_gcp_op_client(parameters)
    add_audit_log(session, task_id, "NetworkOperations", "delete_firewall_rule",
                  "started", TASK_STATUS.COMPLETED)
    try:
        firewall_config_info = parameters.get('firewall_config_info')
    except Exception as ex:
        raise Exception("FW configuration is missing:%s" % str(ex))
    rules_deleted = []
    rules_failed = []
    if firewall_config_info:
        for fw_name in firewall_config_info:
            try:
                LOG.debug("IP Name is:%s" % fw_name, {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_firewall_rule:%s" % fw_name,
                              "started", TASK_STATUS.COMPLETED)
                op = firewall_client.delete(project=parameters.get('gcp_project'),
                                            firewall=fw_name)
                while op.status != compute_v1.Operation.Status.DONE:
                    op = op_client.wait(
                        operation=op.name, zone=parameters.get('zone'),
                        project=parameters.get('gcp_project'))
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_firewall_rule:%s" % fw_name,
                              "Success", TASK_STATUS.COMPLETED)
                rules_deleted.append(fw_name)
            except Exception as ex:
                rules_failed.append(fw_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_firewall_rule:%s" % fw_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "delete_firewall_rule Rules deleted:%s, Rules failed:%s" %
                      (rules_deleted, rules_failed), "Success", TASK_STATUS.COMPLETED)
        if rules_failed:
            add_audit_log(session, task_id, "NetworkOperations", "delete_firewall_rule",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(rules_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "delete_firewall_rule",
                      "No FW information in the request", TASK_STATUS.COMPLETED)