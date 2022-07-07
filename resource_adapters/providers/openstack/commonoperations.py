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


def create_keypair(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("create_keypair Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    keypair_names = parameters.get('keypair_names')
    if isinstance(keypair_names, str):
        keypair_names = [keypair_names]
    for name in keypair_names:
        add_audit_log(session, task_id, "CommonOperation", "create_keypair:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            kp = client.get_keypair(name)
            if kp is not None:
                raise Exception('Keypair {} already exists'.format(name))
            client.create_keypair(name)
        except Exception as ex:
            add_audit_log(session, task_id, "CommonOperation", "create_keypair:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "CommonOperation", "create_keypair:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "CommonOperation", "create_keypair",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_keypair(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_keypair Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    keypair_names = parameters.get('keypair_names')
    if isinstance(keypair_names, str):
        keypair_names = [keypair_names]
    for name in keypair_names:
        add_audit_log(session, task_id, "CommonOperation", "delete_keypair:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            kp = client.get_keypair(name)
            if kp is None:
                raise Exception('Keypair {} does not exist'.format(name))
            client.delete_keypair(name)
        except Exception as ex:
            add_audit_log(session, task_id, "CommonOperation", "delete_keypair:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "CommonOperation", "delete_keypair:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "CommonOperation", "delete_keypair",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_storage_object(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_storage_object Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    object_info = parameters.get('object_info')
    if isinstance(object_info, str):
        object_info = [object_info]
    for data in object_info:
        obj_name = data.get('object_name')
        cont_name = data.get('container_name')
        add_audit_log(session, task_id, "NetworkOperation", "delete_storage_object:%s" % obj_name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            container = list(client.object_store.objects(container=cont_name))
            ext = True
            for x in container:
                val = x.name
                name = val.split('/')
                if name[-1] == '':
                    name = name[-2]
                else:
                    name = name[-1]
                if name == obj_name:
                    client.object_store.delete_object(x,container = cont_name)
                    ext = False

            if ext:
                raise Exception('Object {} does not exist inside container {}'.format(obj_name,cont_name))
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_storage_object:%s" % obj_name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(obj_name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_storage_object:%s" % obj_name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_storage_object",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def disable_project(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("disable_project Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    project_names = parameters.get('project_names')
    if isinstance(project_names, str):
        project_names = [project_names]
    for name in project_names:
        add_audit_log(session, task_id, "NetworkOperation", "disable_project:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            project = client.identity.find_project(name)
            if project is None:
                raise Exception('Project with name {} does not exist'.format(name))
            client.identity.update_project(project.id,is_enabled = False)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "disable_project:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "disable_project:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "disable_project",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def enable_project(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("enable_project Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    project_names = parameters.get('project_names')
    if isinstance(project_names, str):
        project_names = [project_names]
    for name in project_names:
        add_audit_log(session, task_id, "NetworkOperation", "enable_project:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            project = client.identity.find_project(name)
            if project is None:
                raise Exception('Project with name {} does not exist'.format(name))
            client.identity.update_project(project.id,is_enabled = True)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "enable_project:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "enable_project:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "enable_project",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))


def delete_project(parameters, session, **kwargs):
    task_id = parameters.get('task_id')
    LOG.debug("delete_project Openstack op:%s" % parameters, {'task_id': task_id})
    try:
        client = get_openstack_client(parameters)
    except Exception as ex:
        raise ex
    ops_failed = []
    project_names = parameters.get('project_names')
    if isinstance(project_names, str):
        project_names = [project_names]
    for name in project_names:
        add_audit_log(session, task_id, "NetworkOperation", "delete_project:%s" % name,
                    "started", TASK_STATUS.COMPLETED)
        try:
            project = client.identity.find_project(name)
            if project is None:
                raise Exception('Project with name {} does not exist'.format(name))
            client.identity.delete_project(project.id)
        except Exception as ex:
            add_audit_log(session, task_id, "NetworkOperation", "delete_project:%s" % name,
                        str(ex), TASK_STATUS.FAILED)
            ops_failed.append(name)

        add_audit_log(session, task_id, "NetworkOperation", "delete_project:%s" % name,
                        "Success", TASK_STATUS.COMPLETED)
    if ops_failed:
        add_audit_log(session, task_id, "NetworkOperation", "delete_project",
                    "Failed", TASK_STATUS.FAILED)
        raise Exception('Following ops failed {}'.format(ops_failed))