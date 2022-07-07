
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from azure.mgmt.network.models import Subnet, InboundNatRule, \
    FrontendIPConfiguration, Probe
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

def delete_zones(parameters,session):
    task_id = parameters.get('task_id')
    dns_client = get_dns_ops_client(parameters)
    LOG.debug("delete_zones:%s" % parameters,
                {'task_id': task_id})
    add_audit_log(session,task_id,"DnsOperations", "delete_zones",
                        "started", TASK_STATUS.COMPLETED)
    try:
        zone_info = parameters.get('zone_names')
    except Exception as ex:
        raise Exception("Zone info is missing:%s" % str(ex))
    zones_deleted = []
    zones_failed = []
    if zone_info:
        for zone in zone_info:
            try:
                LOG.debug("Zone Name is:%s" % zone, {'task_id': task_id})
                add_audit_log(session,task_id,"DnsOperations", "delete_zones:%s" % zone,
                                    "started", TASK_STATUS.COMPLETED)
                async_delete_zone = dns_client.zones.begin_delete(
                    parameters.get('resource_group_name'), zone)
                async_delete_zone.wait()
                add_audit_log(session,task_id,"DnsOperations", "delete_zones:%s" % zone,
                                    "Success", TASK_STATUS.COMPLETED)
                zones_deleted.append(zone)
            except Exception as ex:
                zones_failed.append(zone)
                add_audit_log(session,task_id,"DnsOperations", "delete_zones:%s" % zone,
                                    "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session,task_id,"DnsOperations",
                            "delete_zones Zones deleted:%s, Zones failed:%s" %
                            (zones_deleted, zones_failed),
                            "Success", TASK_STATUS.COMPLETED)
        if zones_failed:
            add_audit_log(session, task_id, "DnsOperations", "delete_zones",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(zones_failed))
    else:
        add_audit_log(session,task_id,"DnsOperations", "delete_zones",
                            "No Zone information in the request", TASK_STATUS.COMPLETED)

def delete_dns_record_sets(parameters,session):
    task_id = parameters.get('task_id')
    dns_client = get_dns_ops_client(parameters)
    LOG.debug("delete_dns_record_sets:%s" % parameters,
                {'task_id': task_id})
    add_audit_log(session,task_id,"DnsOperations", "delete_dns_record_sets",
                        "started", TASK_STATUS.COMPLETED)
    try:
        zone_info = parameters.get('zone_info')
    except Exception as ex:
        raise Exception("Zone info is missing:%s" % str(ex))
    sets_deleted = []
    sets_failed = []
    if zone_info:
        for zone_data in zone_info:
            set_name = zone_data.get('set_name')
            try:
                zone = zone_data.get('zone')
                set_type = parameters.get('type')
                LOG.debug("Zone Name is:%s" % zone, {'task_id': task_id})
                add_audit_log(session,task_id,"DnsOperations",
                              "delete_dns_record_sets:%s" % set_name,
                              "started", TASK_STATUS.COMPLETED)
                async_delete_set = dns_client.record_sets.delete(
                    parameters.get('resource_group_name'), zone,set_type,set_name)
                async_delete_set.wait()
                add_audit_log(session,task_id,"DnsOperations",
                              "delete_dns_record_sets:%s" % set_name,
                              "Success", TASK_STATUS.COMPLETED)
                sets_deleted.append(set_name)
            except Exception as ex:
                sets_failed.append(set_name)
                add_audit_log(session,task_id,"DnsOperations",
                              "delete_dns_record_sets:%s" % set_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session,task_id,"DnsOperations",
                            "delete_dns_record_sets Sets deleted:%s, Sets failed:%s" %
                            (sets_deleted, sets_failed),
                            "Success", TASK_STATUS.COMPLETED)
        if sets_failed:
            add_audit_log(session, task_id, "DnsOperations", "delete_dns_record_sets",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(sets_failed))
    else:
        add_audit_log(session,task_id,"DnsOperations", "delete_dns_record_sets",
                            "No Zone information in the request", TASK_STATUS.COMPLETED)


def edit_zones(parameters,session):
    task_id = parameters.get('task_id')
    dns_client = get_dns_ops_client(parameters)
    LOG.debug("edit_zones:%s" % parameters,
                {'task_id': task_id})
    add_audit_log(session,task_id,"DnsOperations", "edit_zones",
                        "started", TASK_STATUS.COMPLETED)
    try:
        zone_info = parameters.get('zone_info')
    except Exception as ex:
        raise Exception("Zone info is missing:%s" % str(ex))
    zones_updated = []
    zones_failed = []
    if zone_info:
        for zone_i in zone_info:
            zone = zone_i.get('zone_name')
            try:
                upd_params = zone_i.get('zone_parameters')
                LOG.debug("Zone Name is:%s" % zone, {'task_id': task_id})
                add_audit_log(session,task_id,"DnsOperations", "edit_zones:%s" % zone,
                                    "started", TASK_STATUS.COMPLETED)
                async_update_zone = dns_client.zones.create_or_update(
                    parameters.get('resource_group_name'), zone,upd_params)
                #async_update_zone.wait()
                add_audit_log(session,task_id,"DnsOperations", "edit_zones:%s" % zone,
                                    "Success", TASK_STATUS.COMPLETED)
                zones_updated.append(zone)
            except Exception as ex:
                zones_failed.append(zone)
                add_audit_log(session,task_id,"DnsOperations", "edit_zones:%s" % zone,
                                    "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session,task_id,"DnsOperations",
                            "edit_zones Zones updated:%s, Zones failed:%s" %
                            (zones_updated, zones_failed),
                            "Success", TASK_STATUS.COMPLETED)
        if zones_failed:
            add_audit_log(session, task_id, "DnsOperations", "edit_zones",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(zones_failed))
    else:
        add_audit_log(session,task_id,"DnsOperations", "edit_zones",
                            "No Zone information in the request", TASK_STATUS.COMPLETED)


def edit_dns_record_sets(parameters,session):
    task_id = parameters.get('task_id')
    dns_client = get_dns_ops_client(parameters)
    LOG.debug("edit_dns_record_sets:%s" % parameters,
                {'task_id': task_id})
    add_audit_log(session,task_id,"DnsOperations", "edit_dns_record_sets",
                        "started", TASK_STATUS.COMPLETED)
    try:
        zone_info = parameters.get('zone_info')
    except Exception as ex:
        raise Exception("Zone info is missing:%s" % str(ex))
    sets_updated = []
    sets_failed = []
    if zone_info:
        for zone_data in zone_info:
            set_name = zone_data.get('set_name')
            try:
                zone = zone_data.get('zone')
                set_type = parameters.get('type')
                upd_params = zone_data.get('paramters')
                LOG.debug("Zone Name is:%s" % zone, {'task_id': task_id})
                add_audit_log(session,task_id,"DnsOperations", "edit_dns_record_sets:%s"
                              % set_name,
                              "started", TASK_STATUS.COMPLETED)
                async_update_set = dns_client.record_sets.create_or_update(
                    parameters.get('resource_group_name'), zone,set_name,set_type,upd_params)
                #async_update_set.wait()
                add_audit_log(session,task_id,"DnsOperations", "edit_dns_record_sets:%s"
                              % set_name, "Success", TASK_STATUS.COMPLETED)
                sets_updated.append(set_name)
            except Exception as ex:
                sets_failed.append(set_name)
                add_audit_log(session,task_id,"DnsOperations", "edit_dns_record_sets:%s"
                              % set_name,
                              "%s" % str(ex), TASK_STATUS.FAILED)
        add_audit_log(session,task_id,"DnsOperations",
                            "edit_dns_record_sets Sets updated:%s, Sets failed:%s" %
                            (sets_updated, sets_failed),
                            "Success", TASK_STATUS.COMPLETED)
        if sets_failed:
            add_audit_log(session, task_id, "DnsOperations", "edit_dns_record_sets",
                          "Failed", TASK_STATUS.FAILED)
            raise Exception('Following ops failed {}'.format(sets_failed))
    else:
        add_audit_log(session,task_id,"DnsOperations", "edit_dns_record_sets",
                            "No Zone information in the request", TASK_STATUS.COMPLETED)