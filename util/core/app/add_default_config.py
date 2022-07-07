import os
import yaml
from util.core.app.resources import DatabaseResource
from util.core.app.models import DefaultConfig
from sqlalchemy import or_

def add_default_config(task_payload, session_factory=None):
    print(task_payload)
    payload = task_payload.get('parameters')
    print(payload)
    if not session_factory:
        config_file = os.path.join(os.environ['BASEDIR'],
                                   'configurations',
                                   f'{os.environ["EXECFILE"]}.yml')
        # config_file = "dev.yml"
        if not os.path.exists(config_file):
            config_file = os.path.join(os.environ['BASEDIR'],
                                       'core', 'core', 'settings',
                                       f'{os.environ["EXECFILE"]}.yml')
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
        except Exception as ex:
            raise Exception("Config file not found:%s" % str(ex))
        db = DatabaseResource(
            db_url=config.get('db').get('url'),
            db_schema=config.get('db').get('schema')
        )
        session_factory = db.session
    cloud_provider = task_payload.get('cloud_provider')
    task_name = task_payload.get('task_name')
    with session_factory() as session:
        default_config = session.query(DefaultConfig).where(
            or_(DefaultConfig.cloud_provider.__eq__(cloud_provider),
                DefaultConfig.cloud_provider.__eq__('saas'))).where(
            or_(DefaultConfig.task_name.__eq__(task_name),
                DefaultConfig.task_name.__eq__('all'))).all()

    config_dict = {}
    for data in default_config:
        print(data.cloud_provider, data.task_name, data.default_values)
        if config_dict.get(data.task_name):
            config_dict[data.task_name].append({
                data.cloud_provider: data.default_values})
        else:
            config_dict[data.task_name] = []
            config_dict[data.task_name].append({
                data.cloud_provider: data.default_values})
    print(config_dict)
    if config_dict:
        for task in ['all', task_name]:
            if config_dict.get(task):
                for each_all in config_dict.get(task):
                    for _, cloud_config in each_all.items():
                        if cloud_config:
                            for key, value in cloud_config.items():
                                if not payload.get(key):
                                    payload[key] = value
                                else:
                                    if isinstance(value, dict):
                                        for k, v in value.items():
                                            if not payload[key].get(k):
                                                payload[key][k] = v
                                    elif isinstance(value, list):
                                        for k in value:
                                            payload[key].append(k)
    try:
        if "buffer_size_gb" in payload and "data_disk_info" in payload:
            data_disk_info = payload.get('data_disk_info')
            buffer_size_gb = payload.get('buffer_size_gb')
            for disk_info in data_disk_info:
                if disk_info.get('disk_size_GB'):
                    disk_size = int(disk_info.get('disk_size_GB'))
                    disk_size += buffer_size_gb
                    disk_info['disk_size_GB'] = disk_size

        if "data_disk_info" in payload:
            data_disk_info = payload.get('data_disk_info')
            if "swap_memory_GB" in payload:
                buffer_swap_memory_GB = payload.get('swap_memory_GB')
            elif "buffer_swap_memory_GB" in payload:
                buffer_swap_memory_GB = payload.get('buffer_swap_memory_GB')
            else:
                buffer_swap_memory_GB = 0
            for disk_info in data_disk_info:
                if disk_info.get('disk_size_GB'):
                    disk_size = int(disk_info.get('disk_size_GB'))
                    disk_size += int(buffer_swap_memory_GB)
                    disk_info['disk_size_GB'] = disk_size
    except Exception as ex:
        print("Adding buffer size failed:%s" % ex)

    # If template name is in payload, fetch default template credentials
    if payload.get('template_name') and (not payload.get('template_default_user')
                                         or not payload.get('template_default_password')):
        template_name = payload.get('template_name')
        with session_factory() as session:
            default_config = session.query(DefaultConfig).where(
                DefaultConfig.cloud_provider.__eq__(cloud_provider)).where(
                or_(DefaultConfig.task_name.__eq__(template_name),
                    DefaultConfig.task_name.__eq__('default_template_info'))).all()
        template_info = {}
        for data in default_config:
            print(data.cloud_provider, data.task_name, data.default_values)
            template_info[data.task_name] = data.default_values

        if template_info.get(template_name):
            template_values = template_info.get(template_name)
        else:
            template_values = template_info.get('default_template_info')
        if template_values:
            for key, value in template_values.items():
                payload[key] = value

    # Sort the mount_point configuration if sequence key is available
    fs_config = payload.get('fs_configuration')
    if fs_config:
        try:
            new_fs_config = sorted(fs_config, key=lambda i: i['sequence'])
            payload['fs_configuration'] = new_fs_config
        except Exception as ex:
            print("Sorting failed:%s" % ex)
            payload['fs_configuration'] = fs_config

    print(payload)
    task_payload['parameters'] = payload
    return task_payload
