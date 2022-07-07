import json
import openstack

def get_openstack_client(parameters):
    auth_url = parameters.get('auth_url')
    project_name = parameters.get('tenant_name')
    password = parameters.get('password')
    username = parameters.get('user_name')
    region_name = parameters.get('region')
    project_domain_name = parameters.get('project_domain_name', 'default')
    user_domain_name = parameters.get('user_domain_name', 'default')
    client = openstack.connect(auth_url=auth_url, project_name=project_name,
                               username=username, password=password,
                               region_name=region_name, verify=False,
                               project_domain_name=project_domain_name,
                               user_domain_name=project_domain_name)
    return client
