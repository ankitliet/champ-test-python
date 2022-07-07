'''
`engine.py` file
'''

# GENERATING LOGGER for `base`
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS

from util.core.app.logger import get_logger_func
LOG = get_logger_func(__file__)

'''
: External Imports
    : os
    : sqlalchemy.orm.Session
    : python_terraform
'''
import os
import stat
import git
import time
from cryptography.fernet import Fernet
from typing import Dict
import traceback
import json
import os.path
import subprocess
from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import DeploymentMode


from util.core.app.models import AutomationCode, Credentials
from .exceptions import *

# GLOBAL VARIABLES
ASKPASS_STR = '''
from sys import argv
from os import environ

import sys
print(sys.version_info)

if 'username' in argv[1].lower():
    print(environ['GIT_USERNAME'])
    exit()

if 'password' in argv[1].lower():
    print(environ['GIT_PASSWORD'])
    exit()

exit(1)
'''

class Engine:
    '''
    : `Engine` class that acts as a wrapper over all other utilities/features
    '''
    base_clone_cmd = "git -c http.extraHeader='Authorization: Basic {}' clone {} -b {}"

    def __init__(self, **kwargs):
        self._logger = LOG
        self._conf = kwargs['conf']
        self._db_conn = kwargs['db_conn']
        self._env_vars = kwargs['env_vars']
        self.task_id = "NA"

    def decrypt_password(self, decrypt_text):
        _key = self._conf['Terraform']['decrypt_key']
        cipher_suite = Fernet(_key)
        _pass = bytes(decrypt_text, 'utf-8')
        decode_text = cipher_suite.decrypt(_pass)
        return decode_text.decode('utf-8')

    def clone_via_subprocess(self, subdir: str, token: str, repourl: str, branch: str):
        command = self.base_clone_cmd.format(token, repourl, branch,)
        self._logger.debug(f'Executing clone_via_subprocess started')
        proc = subprocess.Popen(
            command,
            cwd = subdir,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout_value, stderr_value = proc.communicate()
        self._logger.debug("Command output : {} {}".format(stdout_value, stderr_value))
        self._logger.debug(f'Executing clone_via_subprocess end')
        return stdout_value, stderr_value
    
    def clone_repo(self, payload, session, state, **kwargs):
        self._logger.debug(f'cloning git repository into local file system')
        self.add_audit_log(self.task_id, state, "Clone Repo", "Started",
                           TASK_STATUS.COMPLETED)
        try:
            path = os.path.join(self._conf['ARM']['base_clone_path'], payload['task_id'])
            self.create_dir(path)
            filters = [
                getattr(AutomationCode, 'name') == state,
                getattr(AutomationCode, 'cloud_provider') ==
                payload['parameters']['cloud_provider']
            ]
            code = session.query(AutomationCode).filter(*filters).one()
            _creds = session.query(Credentials).filter(Credentials.id==code.cred_id).one()
            password = self.decrypt_password(_creds.password)
            self.clone_via_subprocess(
                subdir=path,
                token=password,
                repourl=code.repo_url,
                branch=code.branch
            )
            self._logger.debug(f'cloning repository complete!')
            self._logger.debug(f'Changing current working directory[{code.script_path}]')
            working_dir = os.path.join(path, code.script_path)
            self.change_dir(working_dir)
            self.add_audit_log (kwargs['task_id'], state, 'CloneRepository', 'Success',
                                TASK_STATUS.COMPLETED)
            return (path, working_dir,)
        except Exception as excp:
            self.add_audit_log (
                kwargs['task_id'], state, 'CloneRepository', 
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)),
                TASK_STATUS.FAILED
            )
            raise CloneError from excp

    def create_dir(self, path: str) -> None:
        '''
        : Creates a directory if it does not exist
        
        : params:
            : path[str]: The directory path as to which the directory has to be created
        '''
        try:
            self._logger.debug("Create Dir:%s" % path, {'task_id': self.task_id})
            os.mkdir(path)
        except FileExistsError as excp:
            self._logger.exception(excp, {'task_id': self.task_id})
            self._logger.warning(f'The dir[{path}] already exists! Hence skipping!',
                                 {'task_id': self.task_id})

    def destroy_dir(self, path: str) -> None:
        '''
        : Deletes a directory
        
        : params:
            : path[str]: The directory path as to which the directory has to be created
        '''
        try:
            self._logger.exception("Destory Dir:%s" % path, {'task_id': self.task_id})
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(path)
        except FileNotFoundError as excp:
            self._logger.exception(excp, {'task_id': self.task_id})
            self._logger.warning(f'The dir[{path}] does not exists! Hence skipping!',
                                 {'task_id': self.task_id})

    def change_dir(self, path: str) -> None:
        try:
            self._logger.exception("change Dir:%s" % path, {'task_id': self.task_id})
            os.chdir(path)
        except FileNotFoundError as excp:
            self._logger.exception(excp, {'task_id': self.task_id})
            raise excp

    def create_askpass(self, path: str):
        self._logger.debug('create_askpass:%s' % path,
                           {'task_id': self.task_id})
        path = os.path.join(path, 'askpass.py')
        if os.path.exists(path) == True:
            return
        else:
            with open(path, 'w') as file:
                file.write(ASKPASS_STR)
            os.chmod(path, stat.S_IRWXO)
            return

    def add_audit_log(self, task_id: str, source: str, event: str, trace: str, status: str):
        payload = {
            "task_id": task_id,
            "source": source,
            "event": event,
            "trace": trace,
            "status": status
        }
        LOG.debug("Insert audit logs:%s" % payload, {'task_id': task_id})
        insert_audit_log(payload, session_factory=self._db_conn._session_factory)
            
    def fetch_arm_template(self, dir_path):
        with open(dir_path, 'r+') as file:
            tmp = json.load(file)
        return tmp
    
    def create_armvar(self, params: dict, templ: dict):
        upd_params = {}
        for key in templ['parameters'].keys():
            if params.get(key):
                upd_params[key] = params[key]
        upd_params = {k: {'value': v} for k, v in upd_params.items()}
        return upd_params
                
    def create_client(self, params: dict):
        credentials = ClientSecretCredential(
            client_id=params['azure_client_id'],
            client_secret=params['azure_client_secret'],
            tenant_id=params['azure_tenant_id']
        )
        client = ResourceManagementClient(credentials, params['azure_subscription_id'])
        return client
    
    def __call__(self, state: str, payload: Dict[str, str], autoinitiate: bool):
        self.task_id = payload.get('task_id', 'NA')
        self._logger.info("AzureARM call:%s" % payload, {'task_id': self.task_id})
        return self._arm_incr_create(state, payload, autoinitiate)
        
    def _arm_incr_create(self, state, payload, autoinitiate):
        task_id = payload.get('task_id', 'NA')
        try:
            self._logger.info('ARMCreate:%s' % payload, {'task_id': task_id})
            self.add_audit_log(task_id, state, "ARM Create", "Started",
                               TASK_STATUS.COMPLETED)
            template_filename = 'main.json'
            with self._db_conn._session_factory() as session:
                if not os.path.exists(self._conf['ARM']['base_clone_path']):
                    self.create_dir(self._conf['ARM']['base_clone_path'])
                self.create_askpass(self._conf['ARM']['base_clone_path'])
                self._logger.info(f'Executing task[{payload["task_id"]}]', {'task_id': task_id})
                dir_path, working_dir = self.clone_repo(
                    payload=payload, session=session, state=state, task_id=payload["task_id"]
                )
                client = self.create_client(params=payload['parameters'])
                templ = self.fetch_arm_template(
                    dir_path=os.path.join(working_dir, template_filename))
                params = self.create_armvar(params=payload['parameters'], templ=templ)
                deployment_properties = {
                    'properties': {
                        'mode': DeploymentMode.incremental,
                        'template': templ,
                        'parameters': params
                    },
                    'location': payload['parameters'].get('location'),
                    'tags': payload['parameters'].get('tags', {})
                }
                self.add_audit_log(task_id, state, 'ARM deployment', 'Started',
                                   TASK_STATUS.COMPLETED)
                deployment_async_operation = client.deployments.begin_create_or_update(
                    payload['parameters']['resource_group_name'],
                    payload['parameters'].get('template_name', 'randomisintro'),
                    deployment_properties
                )
                deployment_async_operation.wait()
                self.add_audit_log(task_id, state, 'ARM deployment', 'Success',
                                   TASK_STATUS.COMPLETED)
                return (payload, 'success',)
        except Exception as excp:
            self._logger.exception(excp, {'task_id': task_id})
#             if payload.get('exceptional_cleanup', True) == True:
#                 time.sleep(self._conf['sleepinterval_before_exceptional_destroy'])
#                 self._logger.warning(f'Initiating arm cleanup...', {'task_id': task_id})
            self._logger.info(f'Destroying dir[{dir_path}]', {'task_id': task_id})
            self.destroy_dir(dir_path)
            self.add_audit_log(payload["task_id"],  state, "CleanDirectory", dir_path,
                               TASK_STATUS.COMPLETED)
            self.add_audit_log(
                payload["task_id"], state, 'ARMExecution',
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)),
                TASK_STATUS.FAILED
            )
            raise excp
