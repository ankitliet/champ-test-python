import json
import time
import os
from functools import reduce, wraps
import xml.etree.ElementTree as ET
import operator
import jenkins
import xmltodict

# GLOBAL VARIABLES
release = f'-{os.environ.get("EXECFILE", "dev")}' if os.environ.get("EXECFILE", "dev") != 'dev' else ''

_cache = {}


def cacheDecorator(refresh_time: int):
    def wrap(func):
        @wraps(func)
        def wrapped_func(*args, **kwargs):
            try:
                if time.time() - _cache[kwargs['name']]['lastfetched'] > refresh_time:
                    _cache.pop(kwargs['name'])
                    raise KeyError
                else:
                    return _cache[kwargs['name']]['value']
            except KeyError:
                value = func(*args, **kwargs)
                _cache[kwargs['name']] = {'value': value, 'lastfetched': time.time()}
                return value

        return wrapped_func

    return wrap


class JenkinsService:

    def __init__(self, config):
        self._server = jenkins.Jenkins(config['host'], username=config['username'], password=config['password'])

    @cacheDecorator(refresh_time=200)
    def get_jobconfig(self, name):
        return xmltodict.parse(self._server.get_job_config(name))['flow-definition']['properties'][
            'hudson.model.ParametersDefinitionProperty']['parameterDefinitions']

    def get_jobparams(self, jobconfig):
        return \
        jobconfig['flow-definition']['properties']['hudson.model.ParametersDefinitionProperty']['parameterDefinitions'][
            'hudson.model.StringParameterDefinition']

    @property
    def user(self):
        return self.user

    @property
    def version(self):
        return self.version

    @classmethod
    def get_by_path(cls, _dict, _path):
        if _path == None:
            return None
        """Access a nested object in root by item sequence."""
        return reduce(operator.getitem, _path, _dict)

    @classmethod
    def set_by_path(cls, _dict, _path, value):
        """Set a value in a nested object in root by item sequence."""
        cls.get_by_path(_dict, _path[:-1])[_path[-1]] = value

    def trigger(self, name, params: dict):
        self._server.crumb = None
        data_dict = {}
        job_parameters = self.get_jobconfig(name=f'{name}{release}')
        for param_type in job_parameters:
            for param in job_parameters[param_type]:
                if isinstance(params.get(param['name']), dict) or isinstance(params.get(param['name']), list):
                    _value = json.dumps(params.get(param['name']), separators=(",", ":"))
                    _value = _value.replace(":", "=")
                elif isinstance(params.get(param['name']), str):
                    _value = str(params.get(param['name'])).replace('"', '')
                else:
                    _value = params.get(param['name'])
               # print("{}-{}-{}".format(param['name'], _value, type(params.get(param['name']))))
                self.set_by_path(_dict=data_dict,
                                 _path=[param['name']],
                                 value=_value)
        build_id = self._server.build_job(f'{name}{release}', data_dict)
        return build_id

    def get_queue_item(self, build_id):
        return self._server.get_queue_item(build_id)

    def get_build_info_by_queue_id(self, queue_id):
        print(self._server.crumb)
        self._server.crumb = None
        while True:
            info = self._server.get_queue_item(queue_id)
            if 'executable' in info:
                return self.get_build_info(info['executable']['number'])
            else:
                time.sleep(30)

    def get_build_info(self, build_id):
        return self._server.get_build_info(self.jobname, build_id)

    def get_nodes(self):
        """
        Lists all the available nodes.

        :return: Returns the list of nodes.
        """
        nodes = self._server.get_nodes()
        for agent in nodes[1:]:
            additional_info = self._server.get_node_info(agent['name'])
            agent.update(additional_info)
        return nodes

    def create_node(self, name, num_executors, node_description, remote_fs, labels, exclusive):
        """
        This function is used to create a node.

        :param name: name of node to create.
        :type name: ``str``

        :param num_executors: number of executors for node.
        :type num_executors: ``int``
        
        :param node_description: Description of node.
        :type node_description: ``str``
        
        :param remote_fs: Remote filesystem location to use.
        :type remote_fs: ``str``
        
        :param labels: Labels to associate with node.
        :type labels: ``str``
        
        :param exclusive: Use this node for tied jobs only.
        :type exclusive: ``bool``

        :return: Returns the Created Node.
        """
        node = self._server.create_node(name, numExecutors=num_executors,
                                        nodeDescription=node_description,
                                        remoteFS=remote_fs, labels=labels,
                                        exclusive=exclusive, launcher='hudson.slaves.JNLPLauncher',
                                        launcher_params={'webSocket': True})
        return node

    def update_node(self, slave, name, remote_fs, num_executors=None, node_description=None, labels=None):
        """
        This function is used to update a node.
        
        :param slave: name of node to be updated.
        :type slave: ``str``

        :param name: name of node to that is being updated.
        :type name: ``str``
        
        :param remote_fs: Remote filesystem location to use.
        :type remote_fs: ``str``

        :param num_executors: number of executors for node. (optional)
        :type num_executors: ``int``
        
        :param node_description: Description of node.(optional)
        :type node_description: ``str``
        
        :param labels: Labels to associate with node. (optional)
        :type labels: ``str``
        
        """
        xml = self._server.get_node_config(slave)
        root = ET.fromstring(xml)

        if name:
            for n in root.iter('name'):
                n.text = str(name)
        if remote_fs:
            for n in root.iter('remoteFS'):
                n.text = str(remote_fs)
        if num_executors:
            for n in root.iter('numExecutors'):
                n.text = str(num_executors)
        if node_description:
            for n in root.iter('description'):
                n.text = str(node_description)
        if labels:
            for n in root.iter('label'):
                n.text = str(labels)

        config_xml = ET.tostring(root, encoding='utf-8', method='xml')
        config_xml = config_xml.decode()
        node = self._server.reconfig_node(slave, config_xml)
        return node
