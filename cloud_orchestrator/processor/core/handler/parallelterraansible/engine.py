'''
`engine.py` file
'''

# GENERATING LOGGER for `base`
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS

import requests, adal, json

# from .logger import getlogger
# logger = getlogger(__file__)

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
from datetime import datetime
from sqlalchemy.orm import Session
from transitions import Machine
from sqlalchemy import and_
import urllib.parse
import subprocess
from cryptography.fernet import Fernet
from typing import Dict, List, Tuple
import traceback
from getpass import getpass
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import threading

from .resource import DatabaseResource
from util.core.app.models import AutomationRequest, AutomationTask, AutomationPlan, \
    AutomationCode, Credentials
from util.core.app.models import Application as CallbackApplication
from .exceptions import *
from .terrawrapper import TerraformWrapper

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
        self._logger = LOG # logger.getlogger(self.__class__.__name__)
        self._conf = kwargs['conf']
        self._mapper = kwargs['mapper']
        self._db_conn = kwargs['db_conn']
        self._env_vars = kwargs['env_vars']
        self.task_id = "NA"
        #self._set_proxy()
        
    def _set_envvars(self):
        for key, value in self._proxy.items():
            os.environ[key] = value
            
    def _unset_envvars(self):
        for key in self._proxy.keys():
            os.environ[key] = ''
            
            
    def _set_proxy(self):
        if os.environ.get('PROXY_ENABLED', 'False') == 'True':
            self._logger.debug(f'setting proxy[http_proxy:{self._env_vars.get("http_proxy")}]')
            self._logger.debug(f'setting proxy[https_proxy:{self._env_vars.get("https_proxy")}]')
            os.environ['http_proxy'] = self._env_vars.get('http_proxy')
            os.environ['https_proxy'] = self._env_vars.get('https_proxy')
        
    def _unset_proxy(self):
        self._logger.debug('Unsetting proxy!')
        os.environ['http_proxy'] = ''
        os.environ['https_proxy'] = ''
       
    
    def decrypt_password(self, decrypt_text):
        _key = self._conf['Terraform']['decrypt_key']
        cipher_suite = Fernet(_key)
        _pass = bytes(decrypt_text, 'utf-8')
        decode_text = cipher_suite.decrypt(_pass)
        return decode_text.decode('utf-8')



    def decp_clone_repo(self, payload, session, state, **kwargs):
        self._logger.debug(f'cloning git repository into local file system')
        try:
            #self._unset_proxy()
            path = os.path.join(self._conf['Terraform']['base_clone_path'], payload['task_id'])
            self.create_dir(path)
            filters = [
                getattr(AutomationCode, 'name') == state,
                getattr(AutomationCode, 'cloud_provider') == payload['parameters']['cloud_provider']
            ]
            code = session.query(AutomationCode).filter(*filters).one()
            _creds = session.query(Credentials).filter(Credentials.id==code.cred_id).one()
            username = _creds.username
            password = self.decrypt_password(_creds.password)
            os.environ['GIT_ASKPASS'] = os.path.join(self._conf['Terraform']['base_clone_path'], 'askpass.py')
            os.environ['GIT_USERNAME'] = _creds.username
            os.environ['GIT_PASSWORD'] = self.decrypt_password(_creds.password)
            self._logger.debug(f'creating git object...', {'task_id': self.task_id})
            _git = git.cmd.Git(path)
            self._logger.debug(f'Initializing empty git dir...', {'task_id': self.task_id})
            _git.init()
            self._logger.debug(f'Initializing remote origin[{code.repo_url}]...',
                               {'task_id': self.task_id})
            _git.remote('add', 'origin', code.repo_url)
            self._logger.debug(f'Pulling branch[{code.branch}]', {'task_id': self.task_id})
            _git.pull('origin', code.branch)
            self._logger.debug(f'cloning repository complete!', {'task_id': self.task_id})
            self._logger.debug(f'Changing current working directory[{code.script_path}]',
                               {'task_id': self.task_id})
            working_dir = os.path.join(path, code.script_path)
            self.change_dir(working_dir)
            #self._set_proxy()
            self.add_audit_log (kwargs['task_id'], state, 'CloneRepository', '',  TASK_STATUS.COMPLETED)
            return (path, working_dir,)
        except Exception as excp:
            self.add_audit_log (
                kwargs['task_id'], state, 'CloneRepository', 
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)),  TASK_STATUS.FAILED
            )
            raise CloneError from excp
            
            
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
        try:
            #self._unset_proxy()
            path = os.path.join(self._conf['Terraform']['base_clone_path'], payload['task_id'])
            self.create_dir(path)
            filters = [
                getattr(AutomationCode, 'name') == state,
                getattr(AutomationCode, 'cloud_provider') == payload['parameters']['cloud_provider']
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
            #self._set_proxy()
            self.add_audit_log (kwargs['task_id'], state, 'CloneRepository', '',  TASK_STATUS.COMPLETED)
            return (path, working_dir,)
        except Exception as excp:
            self.add_audit_log (
                kwargs['task_id'], state, 'CloneRepository', 
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)),  TASK_STATUS.FAILED
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
#             self._logger.exception("Destory Dir:%s" % path, {'task_id': self.task_id})
#             for root, dirs, files in os.walk(path, topdown=False):
#                 for name in files:
#                     os.remove(os.path.join(root, name))
#                 for name in dirs:
#                     os.rmdir(os.path.join(root, name))
#             os.rmdir(path)
            pass
        except FileNotFoundError as excp:
            self._logger.exception(excp, {'task_id': self.task_id})
            self._logger.warning(f'The dir[{path}] does not exists! Hence skipping!',
                                 {'task_id': self.task_id})

    def change_dir(self, path: str) -> None:
        try:
#             self._logger.exception("change Dir:%s" % path, {'task_id': self.task_id})
#             os.chdir(path)
            ...
        except FileNotFoundError as excp:
            self._logger.exception(excp, {'task_id': self.task_id})
            raise excp

    def _tfplan(self, *args, **kwargs):
        self._logger.debug(f'Creating terraform plan', {'task_id': self.task_id})
        opts = {'-detailed-exitcode': 'flagvalue'}
        err_code, stdout, stderr = self._tf.plan(opts=opts, suppress=True)
        if err_code == 1:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'TerraformPlan', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.FAILED
            )
            raise TerraformPlanException(stderr)
        else:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'TerraformPlan', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.COMPLETED
            )
            return stdout

    def _tfapply(self, *args, **kwargs):
        self._logger.debug(f'Applying Terraform Apply', {'task_id': self.task_id})
        opts = {'-auto-approve': 'flagvalue'}
        err_code, stdout, stderr = self._tf.apply(opts=opts, suppress=True)
        if err_code == 1:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'TerraformApply', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.FAILED
            )
            raise TerraformApplyException(stderr)
        else:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'TerraformApply', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.COMPLETED
            )
            return stdout

    def _wrapper(self, _func, task_id, tf_file_path, output_file_path, _session):
        self._logger.debug(f'Using mapping function to create a new mapping!',
                           {'task_id': self.task_id})
        return _func(
            task_id=task_id,
            tf_file_path=tf_file_path,
            output_file_path=output_file_path,
            _session=_session
        )


    def _tfinit(self, terrafrom_init_backend_config: dict, **kwargs):
        self._logger.debug(f'Initializing the terraform object!', {'task_id': self.task_id})
        opts = {'-backend-config': terrafrom_init_backend_config}
        err_code, stdout, stderr = self._tf.init(opts=opts, suppress=True)
        if err_code == 1:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'TerraformInit', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.FAILED
            )
            raise TerraformInitException(stderr)
        else:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'TerraformInit', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.COMPLETED
            )
            return stdout
        
        
    def _tfsetworkspace(self, identifier: str, **kwargs):
        self._logger.debug(f'Creating terraform workspace[{identifier}]',
                           {'task_id': self.task_id})
        opts = {identifier: 'flagvalue'}
        err_code, stdout, stderr = self._tf.set_workspace(opts=opts, suppress=True)
        if err_code == 1:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'SetTerraformWorkspace', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.FAILED
            )
            raise TerraformCreateWorkspaceException(stderr)
        else:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'SetTerraformWorkspace', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.COMPLETED
            )
            return stdout
        
        
    def _tfunsetsetworkspace(self, identifier: str, **kwargs):
        self._logger.debug(f'Creating terraform workspace[{identifier}]',
                           {'task_id': self.task_id})
        opts = {'-force': 'flagvalue', identifier: 'flagvalue'}
        err_code, stdout, stderr = self._tf.unset_workspace(opts=opts, suppress=True)
        if err_code == 1:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'UnsetTerraformWorkspace', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.FAILED
            )
            raise TerraformCreateWorkspaceException(stderr)
        else:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'UnsetTerraformWorkspace', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.COMPLETED
            )
            return stdout

        
    def _tfcreateworkspace(self, identifier: str, **kwargs):
        self._logger.debug(f'Creating terraform workspace[{identifier}]',
                           {'task_id': self.task_id})
        opts = {identifier: 'flagvalue'}
        err_code, stdout, stderr = self._tf.create_workspace(opts=opts, suppress=True)
        if err_code == 1:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'CreateTerraformWorkspace', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.COMPLETED
            )
        else:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'CreateTerraformWorkspace', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.COMPLETED
            )
            return stdout
        
    def _tfdestroy(self, **kwargs):
        self._logger.debug(f'Destroying terraform resources...', {'task_id': self.task_id})
        opts = {'-destroy': 'flagvalue', '-skip-plan': 'true'}
        err_code, stdout, stderr = self._tf.apply(opts=opts, suppress=True)
        if err_code == 1:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'DestroyResources', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.FAILED
            )
            raise TerraformDestroyResourcesException(stderr)
        else:
            self.add_audit_log(
                kwargs['task_id'], kwargs['state'], 'DestroyResources', 
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.COMPLETED
            )
            return stdout

        
    def create_tfvar(self, path: str, payload: dict, session=None, source=None):
        self._logger.debug('create_tfvar:%s' % path, {'task_id': self.task_id})
        if os.path.exists(path) == True:
            return
        else:
            with open(path, 'w') as file:
                json.dump(payload, file)
            return

        
    def create_gcp_auth_file(self, path: str, payload: str, session=None, source=None):
        self._logger.debug('create_gcp_auth_file:%s' % path,
                           {'task_id': self.task_id})
        if os.path.exists(path) == True:
            return
        else:
            credentials = payload.get('parameters').get('credentials')
            with open(path, 'w') as file:
                if isinstance(credentials, str):
                    credentials = json.loads(credentials)
                json.dump(credentials, file)
            return

        
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
            "task_id": self.task_id,
            "source": source,
            "event": event,
            "trace": trace,
            "status": status
        }
        LOG.debug("Insert audit logs:%s" % payload, {'task_id': task_id})
        insert_audit_log(payload, session_factory=self._db_conn._session_factory)

        
    def get_token(self, payload):
        authority_url = 'https://login.microsoftonline.com/' + payload.get('azure_tenant_id')
        context = adal.AuthenticationContext(authority_url, verify_ssl=False)
        resource = 'https://management.azure.com/'
        token = context.acquire_token_with_client_credentials(
            resource, payload.get('azure_client_id'), payload.get('azure_client_secret'))
        return token

    def get_terms(self, payload):
        token = self.get_token(payload)
        headers = {'Authorization': 'Bearer ' + token['accessToken'], 'Content-Type': 'application/json'}
        url = "https://management.azure.com/subscriptions/{}" \
              "/providers/Microsoft.MarketplaceOrdering/offerTypes/virtualmachine/publishers/{}/offers/{}/plans/{}" \
              "/agreements/current?api-version=2015-06-01".format(
            payload.get('azure_subscription_id'), payload.get('vm_os_publisher'),
            payload.get('vm_os_offer'), payload.get('vm_os_sku'))
        response = requests.get(url, headers=headers, verify=False)
        response_json = json.loads(response.content)
        return response_json
    

    def accept_terms(self, payload, state, task_id):
        self._logger.info("Accept terms:%s" % payload, {'task_id': task_id})
        try:
            response = self.get_terms(payload)
            if response and not "error" in response:
                response['properties']['accepted'] = True
                requsest_data = json.dumps(response)
                token = self.get_token(payload)
                headers = {'Authorization': 'Bearer ' + token['accessToken'], 'Content-Type': 'application/json'}
                url = "https://management.azure.com/subscriptions/{}/providers/Microsoft.MarketplaceOrdering" \
                      "/offerTypes/virtualmachine/publishers/{}/offers/{}/plans/{}/agreements/current?api" \
                      "-version=2015-06-01".format(payload.get('azure_subscription_id'),
                                                   payload.get('vm_os_publisher'),
                                                   payload.get('vm_os_offer'), payload.get('vm_os_sku'))
                response = requests.put(url, data=requsest_data, headers=headers, verify=False)
                response_json = json.loads(response.content)
                self.add_audit_log(task_id, state, 'Accept Terms:%s' % response_json,
                                   "Success", TASK_STATUS.COMPLETED)
        except Exception as ex:
            self.add_audit_log(task_id, state, 'Accept Terms', "%s" % str(ex),
                               TASK_STATUS.FAILED)

            
    def __call__(self, state: str, payload: Dict[str, str], autoinitiate: bool):
        self.task_id = payload.get('task_id', 'NA')
        self._logger.info("Terrastate call:%s" % payload, {'task_id': self.task_id})
        if 'rollback' in state:
            return self._terradestroy(state, payload, autoinitiate)
        else:
            return self._terracreate(state, payload, autoinitiate)


    def _terracreate(self, state, payload, autoinitiate):
        task_id = self.task_id
        try:
            self._logger.info('Terracreate:%s' % payload, {'task_id': task_id})
            tf_filename = 'main.tf'
            with self._db_conn._session_factory() as session:
                if not os.path.exists(self._conf['Terraform']['base_clone_path']):
                    self.create_dir(self._conf['Terraform']['base_clone_path'])
                self.create_askpass(self._conf['Terraform']['base_clone_path'])
                self._logger.info(f'Executing task[{payload["task_id"]}]', {'task_id': task_id})
                dir_path, working_dir = self.clone_repo(
                    payload=payload, session=session, state=state, task_id=payload["task_id"]
                )
                self._logger.debug(f'Generating terraform.tfvars.json file from request JSON!',
                                   {'task_id': task_id})
                self.create_tfvar(
                    path=os.path.join(working_dir, "terraform.tfvars.json"),
                    payload=payload['parameters'], session=session, source=payload['source']
                )
                self.add_audit_log(payload["task_id"],  state, 'GenerateTFVars', "Success",
                                   TASK_STATUS.COMPLETED)
                
                if payload.get('parameters').get('cloud_provider') == 'gcp':
                    self._logger.debug(f'Generating GCP auth_cred.json file from request JSON!',
                                       {'task_id': task_id})
                    #if isinstance(cred, str):
                    #    cred = json.loads(cred)
                    self.create_gcp_auth_file(path=os.path.join(working_dir, "auth_cred.json"),
                                      payload=payload, session=session, source=payload['source'])
                    self.add_audit_log(payload["task_id"], state, 'GenerateGCPAuthFile', "Success",
                                       TASK_STATUS.COMPLETED)

                self._logger.debug(f'Creating terraform object in dir[{working_dir}]',
                                   {'task_id': task_id})
                global_opts = {'-chdir': working_dir, }
                self._tf = TerraformWrapper(
                    global_opts=global_opts
                    #var_file=os.path.join(working_dir, "terraform.tfvars.json")
                )
                self._logger.debug(f'Initializing the terraform object!',
                                   {'task_id': task_id})
                self._tfinit(
                    terrafrom_init_backend_config=self._conf['terrafrom_init_backend_config'],
                    task_id=payload['task_id'], 
                    state=state
                )
                self._logger.debug("Payload is:%s" % payload, {'task_id': task_id})
                if payload.get('parameters').get('cloud_provider') == 'azure' and \
                        payload.get('parameters').get('blueprint_name') == 'os-provisioning':
                    self._logger.debug(f'Accepting terms for os-provisioning task',
                                       {'task_id': task_id})
                    self.accept_terms(payload.get('parameters'), state, payload['task_id'])

                self._logger.debug(f'Creating terraform workspace[{payload["task_id"]}]',
                                   {'task_id': task_id})
                self._tfcreateworkspace(
                    f'{payload["task_id"]}_{state}',
                    task_id=payload['task_id'], 
                    state=state
                )
                self._tfsetworkspace(
                    f'{payload["task_id"]}_{state}',
                    task_id=payload['task_id'], 
                    state=state
                )
                self._logger.debug(f'Creating terraform plan', {'task_id': task_id})
                _plan = self._tfplan(
                    task_id=payload['task_id'], 
                    state=state
                )
                if not payload['parameters'].get('test_run', False):
                    self._logger.debug('Executing terraform plan using `tf.apply`...',
                                       {'task_id': task_id})
                    _apply = self._tfapply(
                    task_id=payload['task_id'], 
                    state=state
                    )
                    outp = self._tf.output(opts={'-json': 'flagvalue'}, suppress=True)
                    self._logger.debug(outp)
                    for key, value in json.loads(outp[1]).items():
                        payload['parameters'][key] = value['value']
                    self.add_audit_log(payload["task_id"],  state, 'UpdatedPayload', json.dumps(payload), TASK_STATUS.COMPLETED)
                self._logger.info(f'Destroying dir[{dir_path}]',
                                  {'task_id': task_id})
                self.destroy_dir(dir_path)
                self.add_audit_log(payload["task_id"],  state, 'CleanDirectory', dir_path, TASK_STATUS.COMPLETED)
                return (payload, 'success',)
        except TerraformApplyException as excp:
            self._logger.exception(excp, {'task_id': task_id})
            if payload.get('exceptional_cleanup', True) == True:
                time.sleep(self._conf['sleepinterval_before_exceptional_destroy'])
                self._logger.warning(f'Initiating terraform cleanup...', {'task_id': task_id})
                try:
                    self._tfdestroy(
                        task_id=payload['task_id'], 
                        state=state
                    )
                    self._tfunsetsetworkspace(
                        f'{payload["task_id"]}_{state}',
                        task_id=payload['task_id'], 
                        state=state
                    )
                except Exception as excps:
                    self._logger.exception(excps, {'task_id': task_id})
            self._logger.info(f'Destroying dir[{dir_path}]', {'task_id': task_id})
            self.destroy_dir(dir_path)
            self.add_audit_log(payload["task_id"],  state, "CleanDirectory", dir_path,  TASK_STATUS.COMPLETED)
            raise excp
        except (TerraformPlanException, TerraformInitException, TerraformCreateWorkspaceException, ) as excp:
            self._logger.exception(excp, {'task_id': task_id})
            self._logger.info(f'Destroying dir[{dir_path}]', {'task_id': task_id})
            self.destroy_dir(dir_path)
            self.add_audit_log(payload["task_id"],  state, "CleanDirectory", dir_path,  TASK_STATUS.COMPLETED)
            raise excp
        except FileNotFoundError as excp:
            self._logger.exception(excp, {'task_id': task_id})
            self.add_audit_log(
                payload["task_id"],  state, 'CreatingDirectory', 
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)), TASK_STATUS.FAILED
            )
            raise excp
        except CloneError as excp:
            self._logger.exception(excp, {'task_id': task_id})
            self.add_audit_log(
                payload["task_id"], state, 'RepoCloneError',
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)), TASK_STATUS.FAILED
            )
            raise excp
        except Exception as excp:
            self._logger.exception(excp, {'task_id': task_id})
            self.add_audit_log(
                payload["task_id"], state, 'TerraformExecution',
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)), TASK_STATUS.FAILED
            )
            raise excp
            

    def _terradestroy(self, state: str, payload: Dict[str, str], autoinitiate: bool):
        task_id = payload.get('task_id', 'NA')
        try:
            with self._db_conn._session_factory() as session:
                self._logger.info(f'Executing task[{payload["task_id"]}]', {'task_id': task_id})
                if not os.path.exists(self._conf['Terraform']['base_clone_path']):
                    self.create_dir(self._conf['Terraform']['base_clone_path'])
                self.create_askpass(self._conf['Terraform']['base_clone_path'])
                self._logger.info(f'Executing task[{payload["task_id"]}]', {'task_id': task_id})
                dir_path, working_dir = self.clone_repo(
                    payload=payload, session=session, state=state.rsplit('_', 1)[0], task_id=payload["task_id"]
                )
                self._logger.debug(f'Generating terraform.tfvars.json file from request JSON!',
                                   {'task_id': task_id})
                self.create_tfvar(path=os.path.join(working_dir, "terraform.tfvars.json"),
                                  payload=payload['parameters'])
                self.add_audit_log(payload["task_id"],  state, 'GenerateTFVars', "Success",
                                   TASK_STATUS.COMPLETED)
                self._logger.debug(f'Creating terraform object in dir[{working_dir}]',
                                   {'task_id': task_id})
                self._tf = Terraform(
                    working_dir=working_dir,
                    var_file=os.path.join(working_dir, "terraform.tfvars.json")
                )
                self._logger.debug(f'Initializing the terraform object!', {'task_id': task_id})
                self._tfinit(
                    terrafrom_init_backend_config=self._conf['terrafrom_init_backend_config'],
                    task_id=payload['task_id'], 
                    state=state
                )
                self._tfsetworkspace(
                    f'{payload["task_id"]}_{state.rsplit("_", 1)[0]}',
                    task_id=payload['task_id'], 
                    state=state
                )
                
                self._logger.warning(f'Initiating terraform cleanup...', {'task_id': task_id})
                self._tfdestroy(
                    task_id=payload['task_id'], 
                    state=state
                )
                self._logger.info(f'Destroying dir[{dir_path}]', {'task_id': task_id})
                self.destroy_dir(dir_path)
                self.add_audit_log(payload["task_id"],  state, 'CleanDirectory', dir_path, TASK_STATUS.COMPLETED)
                return (payload, 'success',)
        except FileNotFoundError as excp:
            self._logger.exception(excp, {'task_id': task_id})
            self.add_audit_log(
                payload["task_id"],  state, 'CreatingDirectory', 
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)), TASK_STATUS.FAILED
            )
            raise excp
        except CloneError as excp:
            self._logger.exception(excp, {'task_id': task_id})
            raise excp
            
            
            
            
            
            
            
class ParallelEngine(Engine):
    
    def __call__(self, state: str, payload: Dict[str, str], autoinitiate: bool):
        self.task_id = payload.get('task_id', 'NA')
        self._logger.info("Terrastate call:%s" % payload, {'task_id': self.task_id})
        if 'rollback' in state:
            return self._terradestroy(state, payload, autoinitiate)
        else:
            local_states = payload['parameters']['software_list']
            with ThreadPoolExecutor(max_workers=len(local_states)) as executor:
                wait_for = []
                for st in local_states:
                    tmp_payload = deepcopy(payload)
                    tmp_payload['parameters'].pop('software_list')
                    tmp_payload['parameters'].update(st)
                    tmp_payload['task_id'] = f'{self.task_id}_{st["install_software"]}'
                    self.add_audit_log (
                        None, state, 'DispatchingThread', str({st['install_software']}),  TASK_STATUS.COMPLETED
                    )
                    fut = executor.submit(
                        self._terracreate, state=state, payload=tmp_payload, autoinitiate=autoinitiate
                    )
                    fut.iden = st['install_software']
                    wait_for.append(fut)
                resp = {}
                flg = True
                for fut in as_completed(wait_for):
                    try:
                        resp[fut.iden] = fut.result()
                    except Exception as excp:
                        flg = False
                        resp[fut.iden] = traceback.format_list(traceback.extract_tb(tb=excp.__traceback__))
        if flg == False:
            raise Exception(resp.__repr__())
        return (payload, 'success',)
    
    


    
    
class EngineStateMachine(Engine):
    states = ['raw', 'created_dir', 'set_dir', 'mapped_request', 'created_tf', 'init_tf', 'created_workspace',
              'tf_planned']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.machine = Machine(model=self, states=EngineStateMachine.states, initial='raw')

        self.machine.add_transition(trigger='create_directory', source='raw', dest='created_dir', before='create_dir')
        self.machine.add_transition(trigger='set_directory', source='created_dir', dest='set_dir', before='change_dir')
        self.machine.add_transition(trigger='map_request', source='set_dir', dest='mapped_request', before='_wrapper')
        self.machine.add_transition(trigger='create_tf_object', source='mapped_request', dest='created_tf',
                                    before='_tfcreate')
        self.machine.add_transition(trigger='tf_init', source='created_tf', dest='init_tf', before='create_dir')
        self.machine.add_transition(trigger='create_workspace', source='init_tf', dest='created_workspace',
                                    before='_tfcreateworkspace')
        self.machine.add_transition(trigger='tf_plan', source='created_workspace', dest='tf_planned', before='_tfplan')
