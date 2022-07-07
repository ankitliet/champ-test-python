
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from azure.mgmt.network.models import Subnet, InboundNatRule, \
    FrontendIPConfiguration, Probe, BackendAddressPool
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

#################### Remove backend pool to Application Gateway #################
def remove_backendpool_from_application_gateway(parameters, session, **kwargs):

    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("remove_backendpool_from_application_gateway:%s" % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations",
                  "remove_backendpool_from_application_gateway",
                  "started", TASK_STATUS.COMPLETED)
    try:
        backendpool_config_info = parameters.get('backendpool_info')
    except Exception as ex:
        raise Exception("Subnet configuration is missing:%s" % str(ex))
    created = []
    failed = []
    if backendpool_config_info:
        for backendpool_info in backendpool_config_info:
            location=backendpool_info.get("location")
            resource_group_name = backendpool_info.get("resource_group_name")
            application_gateway_name = backendpool_info.get('application_gateway_name')
            appgateway_backendpool_name = backendpool_info.get('appgateway_backend_pool_name')
            backend_addresses = backendpool_info.get('backend_addresses')
            try:
                LOG.debug("Resource Group Name is:%s Application "
                          "Gateway Name is:%s Backend pool Name is:%s" %
                          (resource_group_name, application_gateway_name,
                           appgateway_backendpool_name),
                          {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "remove_backendpool_from_application_gateway:%s" %
                              appgateway_backendpool_name,
                              "started", TASK_STATUS.COMPLETED)
                 
                appgateway_info = network_client.application_gateways.get(
                        resource_group_name,
                        application_gateway_name=application_gateway_name)
                backend_add_pools_new=[]
                backend_add_pools = appgateway_info.backend_address_pools
                for backend_add_pool in backend_add_pools:
                    print(backend_add_pool)
                    if(backend_add_pool.name==appgateway_backendpool_name):
                        continue
                    else:
                        backend_add_pools_new.append(backend_add_pool)

                async_create_or_update = \
                    network_client.application_gateways.begin_create_or_update(
                    resource_group_name, application_gateway_name,
                {
                
                    "location": appgateway_info.location,
                    "sku": appgateway_info.sku,
                    "backend_address_pools": backend_add_pools_new,
                    "gateway_ip_configurations": appgateway_info.gateway_ip_configurations,
                    "frontend_ip_configurations": appgateway_info.frontend_ip_configurations,
                    "frontend_ports": appgateway_info.frontend_ports,
                    "backend_http_settings_collection": appgateway_info.backend_http_settings_collection,
                    "http_listeners": appgateway_info.http_listeners,
                    "request_routing_rules": appgateway_info.request_routing_rules                                       

                    }
                )
                async_create_or_update.wait()
                add_audit_log(session, task_id, "NetworkOperations",
                              "remove_backendpool_from_application_gateway:%s"
                              % appgateway_backendpool_name,
                              "Success", TASK_STATUS.COMPLETED)
                created.append(appgateway_backendpool_name)
            except Exception as ex:
                failed.append(appgateway_backendpool_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "remove_backendpool_from_application_gateway:%s"
                              % appgateway_backendpool_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "remove_backendpool_to_application_gateway Pool removed:%s,"
                      " Pool failed:%s" %
                      (created, failed), "Success", TASK_STATUS.COMPLETED)
        if failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "remove_backendpool_to_application_gateway",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations",
                      "remove_backendpool_to_application_gateway",
                      "No Backendpool Application Gateway data in the request",
                      TASK_STATUS.COMPLETED)

#################### Add backend pool to Application Gateway #################
def add_backendpool_to_application_gateway(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("add_backendpool_to_application_gateway:%s" % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations",
                  "add_backendpool_to_application_gateway",
                  "started", TASK_STATUS.COMPLETED)
    try:
        backendpool_config_info = parameters.get('backendpool_info')
    except Exception as ex:
        raise Exception("Subnet configuration is missing:%s" % str(ex))
    created = []
    failed = []
    if backendpool_config_info:
        for backendpool_info in backendpool_config_info:
            location=backendpool_info.get("location")
            resource_group_name = backendpool_info.get("resource_group_name")
            application_gateway_name = backendpool_info.get('application_gateway_name')
            appgateway_backendpool_name = backendpool_info.get('appgateway_backend_pool_name')
            backend_addresses = backendpool_info.get('backend_addresses')
            try:
                LOG.debug("Resource Group Name is:%s Application Gateway Name is:%s"
                          " Backend pool Name is:%s" %
                          (resource_group_name, application_gateway_name,
                           appgateway_backendpool_name),
                          {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "add_backendpool_to_application_gateway:%s" %
                              appgateway_backendpool_name,
                              "started", TASK_STATUS.COMPLETED)

                appgateway_info = network_client.application_gateways.get(
                        resource_group_name,
                        application_gateway_name=application_gateway_name)

                backend_add_pools = appgateway_info.backend_address_pools
                for backend_add_pool in backend_add_pools:
                    print(backend_add_pool)
                new_backend_pool = BackendAddressPool(name=appgateway_backendpool_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "create_backendpool_to_application_gateway:%s" %
                              appgateway_backendpool_name,
                              "Success", TASK_STATUS.COMPLETED)
                backend_add_pools.append(new_backend_pool)
                async_create_or_update = \
                    network_client.application_gateways.begin_create_or_update(
                    resource_group_name, application_gateway_name,
                    {
                        "location": appgateway_info.location,
                        "sku": appgateway_info.sku,
                        "backend_address_pools": backend_add_pools,
                        "gateway_ip_configurations": appgateway_info.gateway_ip_configurations,
                        "frontend_ip_configurations": appgateway_info.frontend_ip_configurations,
                        "frontend_ports": appgateway_info.frontend_ports,
                        "backend_http_settings_collection": appgateway_info.backend_http_settings_collection,
                        "http_listeners": appgateway_info.http_listeners,
                        "request_routing_rules": appgateway_info.request_routing_rules                                       

                        }
                    )
                async_create_or_update.wait()
                add_audit_log(session, task_id, "NetworkOperations",
                              "add_backendpool_to_application_gateway:%s" %
                              appgateway_backendpool_name,
                              "Success", TASK_STATUS.COMPLETED)
                created.append(appgateway_backendpool_name)
            except Exception as ex:
                failed.append(appgateway_backendpool_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "add_backendpool_to_application_gateway:%s"
                              % appgateway_backendpool_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "add_backendpool_to_application_gateway Pool added:%s,"
                      " Pool failed:%s" %
                      (created, failed), "Success", TASK_STATUS.COMPLETED)
        if failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "add_backendpool_to_application_gateway",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations",
                      "add_backendpool_to_application_gateway",
                      "No Backendpool Application Gateway data in the request",
                      TASK_STATUS.COMPLETED)

#################### Delete ApplicationGateway ############# 
def delete_application_gateway(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("delete_application_gateway:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations",
                  "delete_application_gateway",
                  "started", TASK_STATUS.COMPLETED)
    try:
        application_gateway = parameters.get('application_gateway')
    except Exception as ex:
        raise Exception("ApplicationGateway is missing:%s" % str(ex))
    deleted = []
    failed = []
    if application_gateway:
        for application_gateway_name in application_gateway:
            try:
                LOG.debug("Application Gateway Name is:%s" % application_gateway_name,
                          {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_application_gateway:%s" % application_gateway_name,
                              "started", TASK_STATUS.COMPLETED)
                async_delete_application_gateway = \
                    network_client.application_gateways.begin_delete(
                    parameters.get('resource_group_name'), application_gateway_name
                )
                async_delete_application_gateway.wait()
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_application_gateway:%s" % application_gateway_name,
                              "Success", TASK_STATUS.COMPLETED)
                deleted.append(application_gateway_name)
            except Exception as ex:
                failed.append(application_gateway_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_application_gateway:%s" % application_gateway_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "delete_application_gateway deleted:%s,"
                      " delete_application_gateway failed:%s" %
                      (deleted, failed),
                      "Success", TASK_STATUS.COMPLETED)
        if failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "delete_application_gateway",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations",
                      "delete_application_gateway",
                      "No ApplicationGateway information in the request",
                      TASK_STATUS.COMPLETED)
#####################################################################################
def delete_public_ip(parameters, session, **kwargs):
    # Delete public ip
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("delete_public_ip:%s" % parameters, {'task_id': task_id})
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
                async_delete_ip = network_client.public_ip_addresses.begin_delete(
                    parameters.get('resource_group_name'), ip_name)
                async_delete_ip.wait()
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
            add_audit_log(session, task_id, "NetworkOperations",
                          "delete_public_ip",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(ips_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "delete_public_ip",
                      "No IP information in the request", TASK_STATUS.COMPLETED)

def delete_nsg(parameters, session, **kwargs):
    # Delete FW rule
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("delete_nsg:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "delete_nsg",
                  "started", TASK_STATUS.COMPLETED)
    try:
        nsg_config_info = parameters.get('nsg_config_info')
    except Exception as ex:
        raise Exception("Network Security Group configuration is missing:%s" % str(ex))
    rules_deleted = []
    rules_failed = []
    if nsg_config_info:
        for nsg_name in nsg_config_info:
            try:
                LOG.debug("Network Security group Name is:%s" % nsg_name,
                          {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_nsg:%s" % nsg_name,
                              "started", TASK_STATUS.COMPLETED)
                async_delete_ip = network_client.network_security_groups.begin_delete(
                    parameters.get('resource_group_name'), nsg_name)
                async_delete_ip.wait()
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_nsg:%s" % nsg_name,
                              "Success", TASK_STATUS.COMPLETED)
                rules_deleted.append(nsg_name)
            except Exception as ex:
                rules_failed.append(nsg_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_nsg:%s" % nsg_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                           "delete_nsg Rules deleted:%s, Rules failed:%s" %
                           (rules_deleted, rules_failed),
                           "Success", TASK_STATUS.COMPLETED)
        if rules_failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "delete_public_ip",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(rules_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "delete_nsg",
                      "No NSG information in the request", TASK_STATUS.COMPLETED)

def add_nsg_to_nic(parameters, session, **kwargs):
    # Add NSG to NIC
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("add_nsg_to_nic:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "add_nsg_to_nic",
                  "started", TASK_STATUS.COMPLETED)
    try:
        nsg_config_info = parameters.get('nic_info')
    except Exception as ex:
        raise Exception("NIC configuration is missing:%s" % str(ex))
    rules_deleted = []
    rules_failed = []
    if nsg_config_info:
        for nsg_info in nsg_config_info:
            nsg_name = nsg_info.get("nsg_name")
            nic_name = nsg_info.get("nic_name")
            try:
                LOG.debug("Nic Name is:%s NSG name is:%s" % (nic_name, nsg_name),
                          {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "add_nsg_to_nic:%s" % nsg_name,
                              "started", TASK_STATUS.COMPLETED)
                nic_info = network_client.network_interfaces.get(
                    parameters.get('resource_group_name'),
                    network_interface_name=nic_name)
                LOG.debug("Nic Info is:%s" % nic_info, {'task_id': task_id})
                ip_configurations = nic_info.ip_configurations

                nsg_data = network_client.network_security_groups.get(
                    parameters.get('resource_group_name'), nsg_name)
                LOG.debug("NSG Info is:%s" % nsg_data, {'task_id': task_id})
                async_update = network_client.network_interfaces.begin_create_or_update(
                    parameters.get('resource_group_name'),
                    nic_name,
                    {
                        "location": parameters.get('location'),
                        "ip_configurations": ip_configurations,
                        "network_security_group": {
                            "id": nsg_data.id,
                            "name": nsg_data.name,
                            "location": nsg_data.location
                        }
                    })
                async_update.wait()
                add_audit_log(session, task_id, "NetworkOperations",
                              "add_nsg_to_nic:%s" % nsg_name,
                              "Success", TASK_STATUS.COMPLETED)
                rules_deleted.append(nsg_name)
            except Exception as ex:
                rules_failed.append(nsg_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "add_nsg_to_nic:%s" % nsg_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "add_nsg_to_nic nic added:%s, nic failed:%s" %
                      (rules_deleted, rules_failed), "Success", TASK_STATUS.COMPLETED)
        if rules_failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "add_nsg_to_nic",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(rules_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "add_nsg_to_nic",
                       "No NSG information in the request", TASK_STATUS.COMPLETED)

def add_nsg_to_subnet(parameters, session, **kwargs):
    # Delete FW rule
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("add_nsg_to_subnet:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "add_nsg_to_subnet",
                  "started", TASK_STATUS.COMPLETED)
    try:
        nsg_config_info = parameters.get('subnet_info')
    except Exception as ex:
        raise Exception("Subnet configuration is missing:%s" % str(ex))
    rules_deleted = []
    rules_failed = []
    if nsg_config_info:
        for nsg_info in nsg_config_info:
            nsg_name = nsg_info.get("nsg_name")
            subnet_name = nsg_info.get('subnet_name')
            vnet_name = nsg_info.get('vnet_name')
            try:
                LOG.debug("Subnet Name is:%s NSG name is:%s" % (subnet_name, nsg_name),
                          {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "add_nsg_to_subnet:%s" % nsg_name,
                              "started", TASK_STATUS.COMPLETED)
                subnet_info = network_client.subnets.get(
                    parameters.get('resource_group_name'),
                    vnet_name,
                    subnet_name)
                LOG.debug("Subnet Info is:%s" % subnet_info, {'task_id': task_id})
                # ip_configurations = nic_info.ip_configurations

                nsg_data = network_client.network_security_groups.get(
                    parameters.get('resource_group_name'), nsg_name)
                LOG.debug("NSG Info is:%s" % nsg_data, {'task_id': task_id})
                async_update = network_client.subnets.begin_create_or_update(
                    parameters.get('resource_group_name'),
                    vnet_name,
                    subnet_name,
                    {
                        "address_prefix": subnet_info.address_prefix,
                        "address_prefixes": [subnet_info.address_prefix],
                        "network_security_group": {
                            "id": nsg_data.id,
                            "name": nsg_data.name,
                            "location": nsg_data.location
                        }
                    })
                async_update.wait()
                add_audit_log(session, task_id, "NetworkOperations",
                              "add_nsg_to_subnet:%s" % nsg_name,
                                   "Success", TASK_STATUS.COMPLETED)
                rules_deleted.append(nsg_name)
            except Exception as ex:
                rules_failed.append(nsg_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "add_nsg_to_subnet:%s" % nsg_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "add_nsg_to_subnet Subnet added:%s, subnet failed:%s" %
                      (rules_deleted, rules_failed), "Success", TASK_STATUS.COMPLETED)
        if rules_failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "add_nsg_to_subnet",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(rules_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "add_nsg_to_subnet",
                           "No NSG information in the request", TASK_STATUS.COMPLETED)

def add_route_table_to_subnet(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("add_route_table_to_subnet:%s" % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations",
                  "add_route_table_to_subnet",
                  "started", TASK_STATUS.COMPLETED)
    try:
        table_config_info = parameters.get('subnet_info')
    except Exception as ex:
        raise Exception("Subnet configuration is missing:%s" % str(ex))
    rules_deleted = []
    rules_failed = []
    if table_config_info:
        for table_info in table_config_info:
            table_name = table_info.get("table_name")
            subnet_name = table_info.get('subnet_name')
            vnet_name = table_info.get('vnet_name')
            try:
                LOG.debug("Subnet Name is:%s Route Table name is:%s" % (subnet_name, table_name),
                          {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "add_route_table_to_subnet:%s" % table_name,
                              "started", TASK_STATUS.COMPLETED)
                subnet_info = network_client.subnets.get(
                    parameters.get('resource_group_name'),
                    vnet_name,
                    subnet_name)
                LOG.debug("Subnet Info is:%s" % subnet_info, {'task_id': task_id})
                # ip_configurations = nic_info.ip_configurations

                table_data = network_client.route_tables.get(
                    parameters.get('resource_group_name'), table_name)
                LOG.debug("Route Table Info is:%s" % table_data, {'task_id': task_id})
                async_update = network_client.subnets.begin_create_or_update(
                    parameters.get('resource_group_name'),
                    vnet_name,
                    subnet_name,
                    {
                        "address_prefix": subnet_info.address_prefix,
                        "address_prefixes": [subnet_info.address_prefix],
                        "route_table": {
                            "id": table_data.id,
                            "name": table_data.name,
                            "location": table_data.location
                        }
                    })
                async_update.wait()
                add_audit_log(session, task_id, "NetworkOperations",
                              "add_route_table_to_subnet:%s" % table_name,
                              "Success", TASK_STATUS.COMPLETED)
                rules_deleted.append(table_name)
            except Exception as ex:
                rules_failed.append(table_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "add_route_table_to_subnet:%s" % table_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "add_route_table_to_subnet Subnet added:%s, subnet failed:%s" %
                      (rules_deleted, rules_failed), "Success", TASK_STATUS.COMPLETED)
        if rules_failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "add_route_table_to_subnet",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(rules_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations",
                      "add_route_table_to_subnet",
                      "No Table information in the request", TASK_STATUS.COMPLETED)

def delete_firewall_rules(parameters, session, **kwargs):
    # Delete FW rule
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("delete_firewall_rules:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "delete_firewall_rules",
                  "started", TASK_STATUS.COMPLETED)
    try:
        firewall_config_info = parameters.get('firewall_config_info')
    except Exception as ex:
        raise Exception("Firewall configuration is missing:%s" % str(ex))
    rules_deleted = []
    rules_failed = []
    if firewall_config_info:
        for fw_name in firewall_config_info:
            try:
                LOG.debug("Network Security group Name is:%s" % fw_name,
                          {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_firewall_rules:%s" % fw_name,
                              "started", TASK_STATUS.COMPLETED)
                async_delete_ip = network_client.azure_firewalls.begin_delete(
                    parameters.get('resource_group_name'), fw_name
                )
                async_delete_ip.wait()
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_firewall_rules:%s" % fw_name,
                              "Success", TASK_STATUS.COMPLETED)
                rules_deleted.append(fw_name)
            except Exception as ex:
                rules_failed.append(fw_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_firewall_rules:%s" % fw_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "delete_firewall_rules Rules deleted:%s, Rules failed:%s" %
                      (rules_deleted, rules_failed), "Success", TASK_STATUS.COMPLETED)
        if rules_failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "delete_firewall_rules",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(rules_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "delete_firewall_rules",
                      "No FW information in the request", TASK_STATUS.COMPLETED)

def delete_vnet(parameters, session, **kwargs):
    # Delete VNet
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("delete_vnet:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "delete_vnet",
                  "started", TASK_STATUS.COMPLETED)
    try:
        vnet_config_info = parameters.get('vnet_config_info')
    except Exception as ex:
        raise Exception("Firewall configuration is missing:%s" % str(ex))
    rules_deleted = []
    rules_failed = []
    if vnet_config_info:
        for vnet_name in vnet_config_info:
            try:
                LOG.debug("Virtaul network Name is:%s" % vnet_name,
                          {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_vnet:%s" % vnet_name,
                              "started", TASK_STATUS.COMPLETED)
                async_delete_ip = network_client.virtual_networks.begin_delete(
                    parameters.get('resource_group_name'), vnet_name
                )
                async_delete_ip.wait()
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_vnet:%s" % vnet_name,
                              "Success", TASK_STATUS.COMPLETED)
                rules_deleted.append(vnet_name)
            except Exception as ex:
                rules_failed.append(vnet_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_vnet:%s" % vnet_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                           "delete_vnet deleted:%s, Vnet failed:%s" %
                           (rules_deleted, rules_failed),
                           "Success", TASK_STATUS.COMPLETED)
        if rules_failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "delete_vnet",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(rules_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "delete_vnet",
                      "No VNet information in the request", TASK_STATUS.COMPLETED)

def delete_subnet(parameters, session, **kwargs):
    # Delete SubNet
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("delete_subnet:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "delete_subnet",
                  "started", TASK_STATUS.COMPLETED)
    try:
        subnet_config_info = parameters.get('subnet_config_info')
    except Exception as ex:
        raise Exception("Subnet configuration is missing:%s" % str(ex))
    rules_deleted = []
    rules_failed = []
    if subnet_config_info:
        for subnet_info in subnet_config_info:
            subnet_name = subnet_info.get('subnet_name')
            vnet_name = subnet_info.get('vnet_name')
            try:
                LOG.debug("VNet:%s Subnet:%s" % (vnet_name, subnet_name),
                          {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_subnet:%s" % subnet_name,
                              "started", TASK_STATUS.COMPLETED)
                async_delete_ip = network_client.subnets.begin_delete(
                    parameters.get('resource_group_name'), virtual_network_name=vnet_name,
                    subnet_name=subnet_name)
                async_delete_ip.wait()
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_subnet:%s" % subnet_name,
                              "Success", TASK_STATUS.COMPLETED)
                rules_deleted.append(subnet_name)
            except Exception as ex:
                rules_failed.append(subnet_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_subnet:%s" % subnet_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "delete_subnet deleted:%s, Vnet failed:%s" %
                      (rules_deleted, rules_failed), "Success", TASK_STATUS.COMPLETED)
        if rules_failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "delete_subnet",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(rules_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "delete_subnet",
                      "No SubNet information in the request", TASK_STATUS.COMPLETED)

def delete_loadbalancer(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("delete_loadbalancer:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "delete_loadbalancer",
                  "started", TASK_STATUS.COMPLETED)
    try:
        loadbalancers = parameters.get('loadbalancer')
        if type(loadbalancers) is str:
            var = [loadbalancers]
            loadbalancers = var
    except Exception as ex:
        raise Exception("Loadbalancer Names are missing:%s" % str(ex))
    rules_deleted = []
    rules_failed = []
    if loadbalancers:
        for lb in loadbalancers:
            try:
                LOG.debug("Load balancer name:%s" % lb,
                          {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations", "delete_loadbalancer:%s" % lb,
                              "started", TASK_STATUS.COMPLETED)
                async_delete_lb = network_client.load_balancers.begin_delete(
                    parameters.get('resource_group_name'), lb)
                async_delete_lb.wait()
                add_audit_log(session, task_id, "NetworkOperations", "delete_loadbalancer:%s" % lb,
                              "Success", TASK_STATUS.COMPLETED)
                rules_deleted.append(lb)
            except Exception as ex:
                rules_failed.append(lb)
                add_audit_log(session, task_id, "NetworkOperations", "delete_loadbalancer:%s" % lb,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "delete_loadbalancer deleted:%s, lbs failed:%s" %
                      (rules_deleted, rules_failed), "Success", TASK_STATUS.COMPLETED)
        if rules_failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "delete_loadbalancer",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(rules_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "delete_loadbalancer",
                      "No Load Balancer information in the request", TASK_STATUS.COMPLETED)

def delete_backend_pool_from_lb(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("delete_backend_pool_from_lb:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "delete_backend_pool_from_lb",
                  "started", TASK_STATUS.COMPLETED)
    try:
        pools = parameters.get('backend_pools')
        if type(pools) is dict:
            var = [pools]
            pools = var
    except Exception as ex:
        raise Exception("Loadbalancer Pools are missing:%s" % str(ex))
    rules_deleted = []
    rules_failed = []
    if pools:
        for pool in pools:
            pool_name = pool.get('backend_pool_name')
            try:
                lb = pool.get('load_balancer_name')
                LOG.debug("Load balancer pool name:%s" % pool_name, {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_backend_pool_from_lb:%s" % pool_name,
                             "started", TASK_STATUS.COMPLETED)
                async_delete_pool = network_client.load_balancer_backend_address_pools.begin_delete(
                    parameters.get('resource_group_name'), lb,pool_name)
                async_delete_pool.wait()
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_backend_pool_from_lb:%s" % pool_name,
                              "Success", TASK_STATUS.COMPLETED)
                rules_deleted.append(pool_name)
            except Exception as ex:
                rules_failed.append(pool_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_backend_pool_from_lb:%s" % pool_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "delete_backend_pool_from_lb deleted:%s, pools failed:%s" %
                      (rules_deleted, rules_failed), "Success", TASK_STATUS.COMPLETED)
        if rules_failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "delete_backend_pool_from_lb",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(rules_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations",
                      "delete_backend_pool_from_lb",
                      "No Load Balancer Backend Pool information in the request",
                      TASK_STATUS.COMPLETED)

def delete_nat(parameters, session, **kwargs):
    # Delete NAT
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("delete_nat:%s" % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "delete_nat",
                  "started", TASK_STATUS.COMPLETED)
    try:
        nat_config_info = parameters.get('nat_config_info')
    except Exception as ex:
        raise Exception("NAT configuration is missing:%s" % str(ex))
    rules_deleted = []
    rules_failed = []
    if nat_config_info:
        for nat_name in nat_config_info:
            try:
                LOG.debug("NAT:%s" % nat_name, {'task_id': task_id})
                add_audit_log(session, task_id, "NetworkOperations", "delete_nat:%s" %
                              nat_name, "started", TASK_STATUS.COMPLETED)
                async_delete_ip = network_client.nat_gateways.begin_delete(
                    parameters.get('resource_group_name'), nat_gateway_name=nat_name)
                async_delete_ip.wait()
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_nat:%s" % nat_name,
                              "Success", TASK_STATUS.COMPLETED)
                rules_deleted.append(nat_name)
            except Exception as ex:
                rules_failed.append(nat_name)
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_nat:%s" % nat_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session, task_id, "NetworkOperations",
                      "delete_nat deleted:%s, Vnet failed:%s" %
                      (rules_deleted, rules_failed), "Success", TASK_STATUS.COMPLETED)
        if rules_failed:
            add_audit_log(session, task_id, "NetworkOperations",
                          "delete_nat",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(rules_failed))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "delete_nat",
                      "No SubNet information in the request", TASK_STATUS.COMPLETED)

def add_inboud_nat_to_lb(parameters, session, **kwargs):
    # Add inboud NAT rule to loadbalancer
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("add_inboud_nat_to_lb:%s" % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "add_inboud_nat_to_lb",
                       "started", TASK_STATUS.COMPLETED)
    try:
        lb_info = parameters.get('loadbalancer_info')
    except Exception as ex:
        raise Exception("loadbalancer configuration is missing:%s" % str(ex))
    if lb_info:
        try:
            lb_name = lb_info.get("lb_name")
            protocol = lb_info.get("protocol")
            name = lb_info.get("nat_rule_name")
            frontend_port = lb_info.get("frontend_port")
            ip_name = lb_info.get("ip_name")
            add_audit_log(session, task_id, "NetworkOperations",
                          "add_inboud_nat_to_lb:%s" % lb_name,
                               "started", TASK_STATUS.COMPLETED)
            lb_details = network_client.load_balancers.get(
                parameters.get('resource_group_name'), lb_name)
            LOG.debug("LB Details:%s" % lb_details, {'task_id': task_id})
            ip_details = network_client.load_balancer_frontend_ip_configurations.get(
                parameters.get('resource_group_name'), lb_name,
                ip_name)
            LOG.debug("IP Details:%s" % ip_details, {'task_id': task_id})
            if lb_details.inbound_nat_rules:
                inbound_nat_rules = lb_details.inbound_nat_rules
            else:
                inbound_nat_rules = []
            frontend_ip_configuration = FrontendIPConfiguration(id=ip_details.id)
            inbound_nat_rules.append(InboundNatRule(
                protocol=protocol, frontend_port=frontend_port,
                name=name, backend_port=frontend_port,
                frontend_ip_configuration=frontend_ip_configuration,))

            for rules in inbound_nat_rules:
                LOG.debug("Rules:%s" % rules, {'task_id': task_id})

            asynch_update = network_client.load_balancers.begin_create_or_update(
                parameters.get('resource_group_name'),
                lb_name,
                {
                    "sku": lb_details.sku,
                    "frontend_ip_configurations": lb_details.frontend_ip_configurations,
                    "location": lb_details.location,
                    "inbound_nat_rules": inbound_nat_rules
                }
            )
            asynch_update.wait()
            add_audit_log(session, task_id, "NetworkOperations",
                          "add_inboud_nat_to_lb:%s" % lb_name,
                          "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperations", "add_inboud_nat_to_lbs",
                          "%s" % str(ex), TASK_STATUS.FAILED)
            raise Exception('Following ops failed:%s' % str(ex))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "add_inboud_nat_to_lb",
                           "No Load Balancer information in the request",
                           TASK_STATUS.COMPLETED)

def remove_lb_rule(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("remove_lb_rule:%s" % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "remove_lb_rule",
                       "started", TASK_STATUS.COMPLETED)
    try:
        lbs_info = parameters.get('loadbalancer_info')
    except Exception as ex:
        raise Exception("loadbalancer configuration is missing:%s" % str(ex))
    if lbs_info:
        for lb_info in lbs_info:
            try:
                lb_name = lb_info.get("lb_name")
                name = lb_info.get("lb_rule_name")
                add_audit_log(session, task_id, "NetworkOperations", "remove_lb_rule:%s" %
                                   lb_name,
                                   "started", TASK_STATUS.COMPLETED)
                lb_details = network_client.load_balancers.get(
                    parameters.get('resource_group_name'), lb_name)
                LOG.debug("LB Details:%s" % lb_details, {'task_id': task_id})
                lb_rules = []
                if lb_details.load_balancing_rules:
                    for lb_rule in lb_details.load_balancing_rules:
                        if lb_rule.name == name:
                            lb_rules.append(lb_rule)
                        else:
                            lb_rules.append(lb_rule)

                for rules in lb_rules:
                    LOG.debug("Rules:%s" % rules, {'task_id': task_id})

                asynch_update = network_client.load_balancers.begin_create_or_update(
                    parameters.get('resource_group_name'),
                    lb_name,
                    {
                        "sku": lb_details.sku,
                        "frontend_ip_configurations": lb_details.frontend_ip_configurations,
                        "location": lb_details.location,
                        "load_balancing_rules": lb_rules
                    }
                )
                asynch_update.wait()
                add_audit_log(session, task_id, "NetworkOperations", "remove_lb_rule:%s" %
                                   lb_name,
                                   "Success", TASK_STATUS.COMPLETED)
            except Exception as ex:
                add_audit_log(session, task_id, "NetworkOperations", "remove_lb_rule",
                                   "%s" % str(ex), TASK_STATUS.FAILED)
                raise Exception('Following ops failed:%s' % str(ex))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "remove_lb_rule",
                           "No Load Balancer information in the request",
                           TASK_STATUS.COMPLETED)

def edit_lb_rule(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("edit_lb_rule:%s" % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "edit_lb_rule",
                       "started", TASK_STATUS.COMPLETED)
    try:
        lbs_info = parameters.get('loadbalancer_info')
    except Exception as ex:
        raise Exception("loadbalancer configuration is missing:%s" % str(ex))
    if lbs_info:
        for lb_info in lbs_info:
            try:
                lb_name = lb_info.get("lb_name")
                info = lb_info.get("lb_rule_info")
                name = info.get('name')
                add_audit_log(session, task_id, "NetworkOperations", "remove_lb_rule:%s" %
                                   lb_name,
                                   "started", TASK_STATUS.COMPLETED)
                lb_details = network_client.load_balancers.get(
                    parameters.get('resource_group_name'), lb_name)
                LOG.debug("LB Details:%s" % lb_details, {'task_id': task_id})
                lb_rules = []
                flag = False
                if lb_details.load_balancing_rules:
                    for lb_rule in lb_details.load_balancing_rules:
                        if lb_rule.name == name:
                            lb_rules.append(info)
                            flag = True
                        else:
                            lb_rules.append(lb_rule)

                if flag == False:
                    lb_rules.append(info)

                for rules in lb_rules:
                    LOG.debug("Rules:%s" % rules, {'task_id': task_id})

                asynch_update = network_client.load_balancers.begin_create_or_update(
                    parameters.get('resource_group_name'),
                    lb_name,
                    {
                        "sku": lb_details.sku,
                        "frontend_ip_configurations": lb_details.frontend_ip_configurations,
                        "location": lb_details.location,
                        "load_balancing_rules": lb_rules
                    }
                )
                asynch_update.wait()
                add_audit_log(session, task_id, "NetworkOperations", "edit_lb_rule:%s" %
                                   lb_name,
                                   "Success", TASK_STATUS.COMPLETED)
            except Exception as ex:
                add_audit_log(session, task_id, "NetworkOperations", "edit_lb_rule",
                                   "%s" % str(ex), TASK_STATUS.FAILED)
                raise Exception('Following ops failed:%s' % str(ex))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "edit_lb_rule",
                           "No Load Balancer information in the request",
                           TASK_STATUS.COMPLETED)

def remove_inboud_nat_from_lb(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    # Remove inboud NAT rule from loadbalancer
    LOG.debug("remove_inboud_nat_from_lb:%s" % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "remove_inboud_nat_from_lb",
                       "started", TASK_STATUS.COMPLETED)
    try:
        lb_info = parameters.get('loadbalancer_info')
    except Exception as ex:
        raise Exception("loadbalancer configuration is missing:%s" % str(ex))
    if lb_info:
        try:
            lb_name = lb_info.get("lb_name")
            name = lb_info.get("nat_rule_name")
            add_audit_log(session, task_id, "NetworkOperations", "remove_inboud_nat_from_lb:%s" %
                               lb_name,
                               "started", TASK_STATUS.COMPLETED)
            lb_details = network_client.load_balancers.get(
                parameters.get('resource_group_name'), lb_name)
            LOG.debug("LB Details:%s" % lb_details, {'task_id': task_id})
            inbound_nat_rules = []
            if lb_details.inbound_nat_rules:
                for nat_rules in lb_details.inbound_nat_rules:
                    if nat_rules.name == name:
                        continue
                    else:
                        inbound_nat_rules.append(nat_rules)

            for rules in inbound_nat_rules:
                LOG.debug("Rules:%s" % rules, {'task_id': task_id})

            asynch_update = network_client.load_balancers.begin_create_or_update(
                parameters.get('resource_group_name'),
                lb_name,
                {
                    "sku": lb_details.sku,
                    "frontend_ip_configurations": lb_details.frontend_ip_configurations,
                    "location": lb_details.location,
                    "inbound_nat_rules": inbound_nat_rules
                }
            )
            asynch_update.wait()
            add_audit_log(session, task_id, "NetworkOperations", "remove_inboud_nat_from_lb:%s" %
                               lb_name,
                               "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperations", "remove_inboud_nat_from_lb",
                               "%s" % str(ex), TASK_STATUS.FAILED)
            raise Exception('Following ops failed:%s' % str(ex))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "remove_inboud_nat_from_lb",
                           "No Load Balancer information in the request",
                           TASK_STATUS.COMPLETED)

def add_health_probe_to_lb(parameters, session, **kwargs):
    # Add Health probe to loadbalancer
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("add_health_probe_to_lb:%s" % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "add_health_probe_to_lb",
                       "started", TASK_STATUS.COMPLETED)
    try:
        lb_info = parameters.get('loadbalancer_info')
    except Exception as ex:
        raise Exception("loadbalancer configuration is missing:%s" % str(ex))
    if lb_info:
        try:
            lb_name = lb_info.get("lb_name")
            protocol = lb_info.get("protocol")
            name = lb_info.get("health_probe_name")
            port = lb_info.get("port")
            interval_in_seconds = lb_info.get("interval_in_seconds")
            number_of_probes = lb_info.get("number_of_probes")

            add_audit_log(session, task_id, "NetworkOperations",
                          "add_health_probe_to_lb:%s" % lb_name,
                          "started", TASK_STATUS.COMPLETED)
            lb_details = network_client.load_balancers.get(
                parameters.get('resource_group_name'), lb_name)
            LOG.debug("LB Details:%s" % lb_details, {'task_id': task_id})
            if lb_details.probes:
                probes = lb_details.probes
            else:
                probes = []
            for health_probe in probes:
                LOG.debug("Health Probe:%s" % health_probe, {'task_id': task_id})
            probes.append(Probe(
                protocol=protocol, port=port,
                name=name, interval_in_seconds=interval_in_seconds,
                number_of_probes=number_of_probes))

            asynch_update = network_client.load_balancers.begin_create_or_update(
                parameters.get('resource_group_name'),
                lb_name,
                {
                    "sku": lb_details.sku,
                    "frontend_ip_configurations": lb_details.frontend_ip_configurations,
                    "location": lb_details.location,
                    "probes": probes
                }
            )
            asynch_update.wait()
            add_audit_log(session, task_id, "NetworkOperations", "add_health_probe_to_lb:%s" % lb_name,
                               "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperations", "add_health_probe_to_lb",
                               "%s" % str(ex), TASK_STATUS.FAILED)
            raise Exception('Following ops failed:%s' % str(ex))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "add_health_probe_to_lb",
                           "No Load Balancer information in the request",
                           TASK_STATUS.COMPLETED)

def remove_health_probe_from_lb(parameters, session, **kwargs):
    # Remove Health probe from loadbalancer
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("remove_health_probe_from_lb:%s" % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "remove_health_probe_from_lb",
                       "started", TASK_STATUS.COMPLETED)
    try:
        lb_info = parameters.get('loadbalancer_info')
    except Exception as ex:
        raise Exception("loadbalancer configuration is missing:%s" % str(ex))
    if lb_info:
        try:
            lb_name = lb_info.get("lb_name")
            name = lb_info.get("health_probe_name")

            add_audit_log(session, task_id, "NetworkOperations",
                          "remove_health_probe_from_lb:%s" % lb_name,
                          "started", TASK_STATUS.COMPLETED)
            lb_details = network_client.load_balancers.get(
                parameters.get('resource_group_name'), lb_name)
            LOG.debug("LB Details:%s" % lb_details, {'task_id': task_id})
            probes = []
            if lb_details.probes:
                for probe in lb_details.probes:
                    if probe.name == name:
                        continue
                    else:
                        probes.append(probe)
            for health_probe in probes:
                LOG.debug("Health Probe:%s" % health_probe, {'task_id': task_id})
            asynch_update = network_client.load_balancers.begin_create_or_update(
                parameters.get('resource_group_name'),
                lb_name,
                {
                    "sku": lb_details.sku,
                    "frontend_ip_configurations": lb_details.frontend_ip_configurations,
                    "location": lb_details.location,
                    "probes": probes
                }
            )
            asynch_update.wait()
            add_audit_log(session, task_id, "NetworkOperations",
                          "remove_health_probe_from_lb:%s" % lb_name,
                          "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperations",
                          "remove_health_probe_from_lb",
                          "%s" % str(ex), TASK_STATUS.FAILED)
            raise Exception('Following ops failed:%s' % str(ex))
    else:
        add_audit_log(session, task_id, "NetworkOperations", "remove_health_probe_from_lb",
                           "No Load Balancer information in the request",
                           TASK_STATUS.COMPLETED)

def delete_virtual_network_gateway(parameters, session, **kwargs): 
    # Delete Virtual Network Gateway
    task_id = parameters.get('task_id')
    network_client = get_network_client(parameters)
    LOG.debug("delete_virtual_network_gateway: %s" % parameters,
              {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "delete_virtual_network_gateway",
                       "started", TASK_STATUS.COMPLETED)
    try:
        virtual_network_gateway_list = parameters.get("virtual_network_gateway_info")
    except Exception as ex:
        add_audit_log(session, task_id, "NetworkOperations", "delete_virtual_network_gateway",
                      "Virtual network gateway configuration is missing: %s" % str(ex),
                      TASK_STATUS.FAILED)
        raise Exception("Virtual network gateway configuration is missing: %s" % str(ex))
    
    if virtual_network_gateway_list:
        for vn_gateway in virtual_network_gateway_list:
            try:
                resource_group_name = vn_gateway.get('resource_group_name')
                virtual_network_gateway_name = vn_gateway.get('gateway_name')
                add_audit_log(session, task_id, "NetworkOperations",
                              "delete_virtual_network_gateway:[{%s}] for resource_group:[{%s}]" 
                              %(virtual_network_gateway_name, resource_group_name),
                              "started", TASK_STATUS.COMPLETED)
                task  = network_client.virtual_network_gateways.begin_delete(resource_group_name,
                                                                            virtual_network_gateway_name)
                task.wait()
                add_audit_log(session, task_id, "NetworkOperations", 
                              "delete_virtual_network_gateway:[{%s}] for resource_group:[{%s}]" 
                              %(virtual_network_gateway_name, resource_group_name),
                              "Success.", TASK_STATUS.COMPLETED)
            except Exception as ex:
                add_audit_log(session, task_id, "NetworkOperations", "delete_virtual_network_gateway",
                          "Failed to delete virtual network gateway from resource group : %s" % str(ex),
                          TASK_STATUS.FAILED)
                raise Exception("Failed to delete virtual network gateway from resource group : %s" % str(ex))    