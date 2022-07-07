from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from resource_adapters.utils.openstack_clients import get_openstack_client
#from pyVmomi import vim

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

#deploy_trigger
def delete_security_group(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_security_group Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    group_names = parameters.get('group_names')
    if isinstance(group_names, str):
        group_names = [group_names]
    for name in group_names:
        add_audit_log(session, task_id, "NetworkOperation", "delete_security_group:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            client.delete_security_group(name)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_security_group:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_security_group:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_security_group",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_security_group_rules(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_security_group_rules Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    rule_ids = parameters.get('rule_ids')
    if isinstance(rule_ids, str):
        rule_ids = [rule_ids]
    for name in rule_ids:
        add_audit_log(session, task_id, "NetworkOperation", "delete_security_group_rules:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            client.network.delete_security_group_rule(name)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_security_group_rules:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_security_group_rules:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_security_group_rules",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_network(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_network Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    network_names = parameters.get('network_names')
    if isinstance(network_names, str):
        network_names = [network_names]
    for name in network_names:
        add_audit_log(session, task_id, "NetworkOperation", "delete_network:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            network = client.network.find_network(name)
            if network is None:
                raise Exception('No Network named {} found'.format(name))
            client.delete_network(name)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_network:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_network:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_network",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_load_balancers(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_load_balancers Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    lb_names = parameters.get('lb_names')
    if isinstance(lb_names, str):
        lb_names = [lb_names]
    for name in lb_names:
        add_audit_log(session, task_id, "NetworkOperation", "delete_load_balancers:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            lb = client.network.find_load_balancer(name)
            if lb is None:
                raise Exception('Load balancer named {} not found'.format(name))
            client.network.delete_load_balancer(lb.id)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_load_balancers:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_load_balancers:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_load_balancers",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_subnet(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("Delete Subnet:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "delete_subnet",
                  "started", TASK_STATUS.COMPLETED)
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
        
    subnet_names = parameters.get('subnet_names')
    s_deleted=[]
    s_failed=[]
    if isinstance(subnet_names, str):
        subnet_names = [subnet_names]
    for name in subnet_names:
        add_audit_log(session, task_id, "NetworkOperation", "delete_subnet:%s" % name,
                        "started", TASK_STATUS.COMPLETED)
        try:         
            response=client.delete_subnet(name)
            if response is True:
                add_audit_log(session, task_id, "NetworkOperation", "delete_subnet:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
                s_deleted.append(name)
            else:
                s_failed.append(name)
                add_audit_log(session, task_id, "NetworkOperation", "delete_subnet:%s" % name,
                        'failed', TASK_STATUS.FAILED)

        except Exception as ex:
            s_failed.append(subnet_names)
            add_audit_log(session, task_id, "NetworkOperation", "delete_subnet:%s" % name,
                        str(ex), TASK_STATUS.FAILED)

        add_audit_log(session, task_id, "NetworkOperation",
              "delete_subnet deleted:%s, failed:%s" %
              (s_deleted, s_failed), "Success", TASK_STATUS.COMPLETED)
    
    if s_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_subnet",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(s_failed))


def delete_floating_ip(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_floating_ip Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    ips_ids = parameters.get('ips_ids')
    if isinstance(ips_ids, str):
        ips_ids = [ips_ids]
    for name in ips_ids:
        add_audit_log(session, task_id, "NetworkOperation", "delete_floating_ip:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            val = client.get_floating_ip(name)
            if val is None:
                raise Exception('No Floating ip with id {} exists'.format(name))
            client.delete_floating_ip(name)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_floating_ip:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_floating_ip:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_floating_ip",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_lb_pool(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_lb_pool Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    pool_names = parameters.get('pool_names')
    if isinstance(pool_names, str):
        pool_names = [pool_names]
    for name in pool_names:
        add_audit_log(session, task_id, "NetworkOperation", "delete_lb_pool:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            pool = client.network.find_pool(name)
            if pool is None:
                raise Exception('Pool with name {} not found'.format(name))
            client.network.delete_pool(pool.id)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_lb_pool:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_lb_pool:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_lb_pool",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_router(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_router:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "delete_router",
                  "started", TASK_STATUS.COMPLETED)
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
        
    router_id = parameters.get('router_id')
    ops_failed=[]
    if isinstance(router_id, str):
        router_id = [router_id]
    for id in router_id:
        add_audit_log(session, task_id, "NetworkOperation", "delete_router:%s" % id,
                        "started", TASK_STATUS.COMPLETED)
        router = client.network.get_router(id)
        try:
            if router is None:
                raise Exception('Router named {} not found'.format(id))
            client.network.delete_router(router)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_router:%s" % id,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(router.name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_router:%s" % id,
                        "Success", TASK_STATUS.COMPLETED)
    
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_router",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_lb_pool_member(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_lb_pool_member Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    pool_info = parameters.get('pool_info')
    if isinstance(pool_info, str):
        pool_info = [pool_info]
    for data in pool_info:
        name = data.get('member_name_or_id')
        pool_name = data.get('pool_name')
        add_audit_log(session, task_id, "NetworkOperation", "delete_lb_pool_member:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            pool = client.network.find_pool(pool_name)
            pool_m = client.network.find_pool_member(name,pool.id)
            if pool is None:
                raise Exception('Pool with name {} not found'.format(pool_name))
                
            if pool_m is None or 'id' not in dict(pool_m):
                raise Exception('Pool member with name {} not found in pool {}'.format(name,pool_name))
            client.network.delete_pool_member(pool_m.id,pool.id)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_lb_pool_member:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)
            continue
        
        add_audit_log(session, task_id, "NetworkOperation", "delete_lb_pool_member:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_lb_pool_member",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_lb_listener(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_lb_listener:%s" % parameters, {'task_id': task_id})
    
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
        
    listener_names = parameters.get('listener_names')
    ops_failed=[]
    if isinstance(listener_names, str):
        listener_names = [listener_names]
    for name in listener_names:
        add_audit_log(session, task_id, "NetworkOperation", "delete_lb_listener:%s" % name,
                        "started", TASK_STATUS.COMPLETED)
        try:
            lst = client.network.find_listener(name)
            
            if lst is None:
                raise Exception('Load balancer listener named {} not found'.format(name))
                
            client.network.delete_listener(lst.id)
            
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_lb_listener:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_lb_listener:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_lb_listener",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_subnet_routes(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_subnet_routes Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    subnet_info = parameters.get('subnet_info')
    if isinstance(subnet_info, str):
        subnet_info = [subnet_info]
    for name in subnet_info:
        add_audit_log(session, task_id, "NetworkOperation", "delete_subnet_routes:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            subnet = client.get_subnet(name)
            if subnet is None or 'id' not in dict(subnet):
                raise Exception('Subnet with name {} not found'.format(name))
            client.network.update_subnet(subnet.id,host_routes = [])
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_subnet_routes:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_subnet_routes:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_subnet_routes",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_subnet_pools(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_subnet_pools Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    subnet_info = parameters.get('subnet_info')
    if isinstance(subnet_info, str):
        subnet_info = [subnet_info]
    for name in subnet_info:
        add_audit_log(session, task_id, "NetworkOperation", "delete_subnet_pools:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            subnet = client.get_subnet(name)
            if subnet is None or 'id' not in dict(subnet):
                raise Exception('Subnet with name {} not found'.format(name))
            client.network.update_subnet(subnet.id,allocation_pools = [])
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_subnet_pools:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_subnet_pools:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_subnet_pools",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_storage_container(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_storage_container Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    container_names = parameters.get('container_names')
    if isinstance(container_names, str):
        container_names = [container_names]
    for name in container_names:
        add_audit_log(session, task_id, "NetworkOperation", "delete_storage_container:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            container = client.get_container(name)
            if container is None:
                raise Exception('Storage Container with name {} not found'.format(name))
            client.delete_container(name)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_storage_container:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_storage_container:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_storage_container",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))

def create_storage_container(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("create_storage_container Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    container_names = parameters.get('container_names')
    if isinstance(container_names, str):
        container_names = [container_names]
    for name in container_names:
        add_audit_log(session, task_id, "NetworkOperation", "create_storage_container:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            container = client.get_container(name)
            if container is not None:
                raise Exception('Storage Container with name {} already exists'.format(name))
            client.create_container(name)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "create_storage_container:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "create_storage_container:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "create_storage_container",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def remove_nic_from_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("remove_nic_from_vm Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    net_info = parameters.get('net_info')
    if isinstance(net_info, str):
        net_info = [net_info]
    for data in net_info:
        name = data.get('network_name')
        vm_name = data.get('vm_name')
        add_audit_log(session, task_id, "NetworkOperation", "remove_nic_from_vm:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            server = client.get_server(vm_name)
            if server is None:
                raise Exception('Server with name {} does not exist'.format(vm_name))
            interfaces = list(client.compute.server_interfaces(server.id))
            network = client.network.find_network(name)
            if network is None:
                raise Exception('Network with name {} does not exist'.format(name))
            ext = True
            for intf in interfaces:
                if intf.net_id == network.id:
                    client.compute.delete_server_interface(intf,server['id'])
                    ext = False
            if ext:
                raise Exception('Network interface for Network {} does not exist inside vm {}'.format(name,vm_name))
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "remove_nic_from_vm:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "remove_nic_from_vm:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "remove_nic_from_vm",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))

def delete_router_interface(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_router_interface:%s" % parameters, {'task_id': task_id})
    
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    
    interface_info = parameters.get('interface_info')
    ops_failed=[]
    
    if isinstance(interface_info, str):
        interface_info = [interface_info]
        
    for data in interface_info:
        id= data.get('router_id')
        subnet_name=data.get('subnet_name')
        add_audit_log(session, task_id, "NetworkOperation", "delete_router_interface:%s" % data,
                        "started", TASK_STATUS.COMPLETED)
        try:
            router=client.network.get_router(id)
            if router is None:
                raise Exception('Router named {} not found'.format(id))
                
            subnet=client.get_subnet(subnet_name)
            if subnet is None:
                raise Exception('Router named {} not found'.format(subnet_name))
                
            client.network.remove_interface_from_router(router=router.id, subnet_id=subnet.id)
            
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_router_interface:%s" % data,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(data)

        add_audit_log(session, task_id, "NetworkOperation", "delete_router_interface:%s" % data,
                        "Success", TASK_STATUS.COMPLETED)
    
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_router_interface",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))

def remove_subnet_from_vm(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("remove_subnet_from_vm Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    subnet_info = parameters.get('subnet_info')
    if isinstance(subnet_info, str):
        subnet_info = [subnet_info]
    for data in subnet_info:
        name = data.get('subnet_name')
        vm_name = data.get('vm_name')
        add_audit_log(session, task_id, "NetworkOperation", "remove_subnet_from_vm:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            server = client.get_server(vm_name)
            if server is None:
                raise Exception('Server with name {} does not exist'.format(vm_name))
            interfaces = list(client.compute.server_interfaces(server.id))
            subnet = client.get_subnet(name)
            if subnet is None:
                raise Exception('Subnet {} does not exist'.format(name))
            ack = True
            for intf in interfaces:
                if intf.fixed_ips == None or len(intf.fixed_ips) == 0:
                    continue
                fixed_ips = intf.fixed_ips[0]
                if fixed_ips.get('subnet_id') == subnet.id:
                    client.compute.delete_server_interface(intf,server.id)
                    ack = False
            if ack:
                raise Exception('Network interface for subnet {} does not exist inside vm {}'.format(name,vm_name))
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "remove_subnet_from_vm:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "remove_subnet_from_vm:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "remove_subnet_from_vm",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_router_routes(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_router_routes:%s" % parameters, {'task_id': task_id})
    add_audit_log(session, task_id, "NetworkOperations", "delete_router_routes",
                  "started", TASK_STATUS.COMPLETED)
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
        
    router_name_or_id = parameters.get('router_name_or_id')
    ops_failed=[]
    if isinstance(router_name_or_id, str):
        router_name_or_id = [router_name_or_id]
    for name in router_name_or_id:
        add_audit_log(session, task_id, "NetworkOperation", "delete_router_routes:%s" % name,
                        "started", TASK_STATUS.COMPLETED)
        router = client.get_router(name, filters=None)
        try:
            if router is None:
                raise Exception('Router_route named {} not found'.format(name))
            if router.routes==[]:
                raise Exception('Router_route named {} has no routes'.format(name))
                
            client.network.update_router(router.id, routes=[])
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_router_routes:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(router.name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_router_routes:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_router_routes",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_lb_monitor(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_lb_monitor Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    monitor_id = parameters.get('monitor_id')
    if isinstance(monitor_id, str):
        monitor_id = [monitor_id]
    for id in monitor_id:
        add_audit_log(session, task_id, "NetworkOperation", "delete_lb_monitor:%s" % id,
                    "started", TASK_STATUS.COMPLETED)
        try:
            monitor = client.network.get_health_monitor(id)
            
            if monitor is None or 'id' not in dict(monitor):
                raise Exception('monitor with name {} not found'.format(id))
                
            client.network.delete_health_monitor(monitor.id)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_lb_monitor:%s" % id,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(id)

        add_audit_log(session, task_id, "NetworkOperation", "delete_lb_monitor:%s" % id,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_lb_monitor",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))