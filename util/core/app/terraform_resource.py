import base64
import os
import stat
import git
from datetime import datetime
from python_terraform import *
from sqlalchemy import and_
import urllib.parse
from typing import Dict, List, Tuple
import traceback
from getpass import getpass
import json
from cryptography.fernet import Fernet
import yaml
import sqlalchemy.exc
from sqlalchemy import exc as sqexcp
from processor.core.handler.terrastate.exceptions import TerraformPlanException, TerraformCreateWorkspaceException
from processor.core.handler.terrastate.terrawrapper import TerraformWrapper
from util.core.app.models import AutomationCode, Credentials, get_states_model, Infracost
from util.core.app.audit_log_transaction import insert_audit_log, insert_infracost
from util.core.app.constants import TASK_STATUS

from util.core.app.logger import get_logger_func

LOG = get_logger_func(__file__)

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

IMPORT_RESOURCE_STR = {
    "azure": {
        "add_disk": "azurerm_managed_disk"
    },
    "gcp": {
        "add_disk": "google_compute_disk"
    }
}


class TerraformClass:
    # base_clone_cmd = "git -c http.extraHeader='Authorization: Basic {}' clone {} -b {}"
    base_clone_cmd = "git clone https://{}:x-oauth-basic@{} -b {}"

    def __init__(self, **kwargs):
        self._conf = kwargs.get('config')
        self._db_conn = kwargs.get('db_conn')
        self._env_vars = kwargs.get('env_vars')
        self.task_id = kwargs.get('task_id')
        # self._set_proxy()
        LOG.debug("Terraform init", {'task_id': self.task_id})

    def _set_proxy(self):
        if os.environ.get('PROXY_ENABLED', 'False') == 'True':
            os.environ['http_proxy'] = self._env_vars.get('http_proxy')
            os.environ['https_proxy'] = self._env_vars.get('https_proxy')

    def _unset_proxy(self):
        os.environ['http_proxy'] = ''
        os.environ['https_proxy'] = ''

    def decrypt_password(self, decrypt_text):
        _key = self._conf['Terraform']['decrypt_key']
        cipher_suite = Fernet(_key)
        _pass = bytes(decrypt_text, 'utf-8')
        decode_text = cipher_suite.decrypt(_pass)
        return decode_text.decode('utf-8')

    def create_gcp_auth_file(self, path: str, payload: dict, session=None, source=None):
        LOG.debug('create_gcp_auth_file:%s' % path,
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

    def depc_clone_repo(self, session, state, payload, ids):
        try:
            path = os.path.join(self._conf['Terraform']['base_clone_path'],
                                self.task_id)
            self.create_dir(path)
            filters = [
                getattr(AutomationCode, 'name') == state,
                getattr(AutomationCode, 'cloud_provider') ==
                payload['cloud_provider']
            ]
            code = session.query(AutomationCode).filter(*filters).one()
            creds = session.query(Credentials).filter(Credentials.id == code.cred_id).one()
            os.environ['GIT_ASKPASS'] = \
                os.path.join(self._conf['Terraform']['base_clone_path'], 'askpass.py')
            os.environ['GIT_USERNAME'] = creds.username
            os.environ['GIT_PASSWORD'] = self.decrypt_password(creds.password)
            # self._unset_proxy()
            _git = git.cmd.Git(path)
            _git.init()
            _git.remote('add', 'origin', code.repo_url)
            _git.pull('origin', code.branch)
            # self._set_proxy()
            # path = "C:/projects/statemachine/terraform_new"
            working_dir = os.path.join(path, 'data')
            self.change_dir(working_dir)
            # Update main.tf file for import resource
            file_path = os.path.join(working_dir, 'main.tf')
            added_str = ""
            for i in range(len(ids)):
                added_str += "resource \"%s\" \"%s%s\" {}" % \
                             (IMPORT_RESOURCE_STR[payload.get('cloud_provider')][state],
                              state, i + 1)
                if len(ids) > 1:
                    added_str += "\n"
            with open(file_path, "a") as f:
                f.write("\n")
                f.write(added_str)
            self.change_dir(working_dir)
            # self._set_proxy()
            return path, working_dir
        except Exception as excp:
            raise excp

    def clone_via_subprocess(self, subdir: str, token: str, repourl: str, branch: str):
        command = self.base_clone_cmd.format(token, repourl, branch, )
        LOG.debug("clone_via_subprocess:%s" % command, {'task_id': self.task_id})
        proc = subprocess.Popen(
            command,
            cwd=subdir,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout_value, stderr_value = proc.communicate()
        return stdout_value, stderr_value

    def clone_repo(self, session, state, payload, ids):
        LOG.debug("clone_repo:%s" % payload, {'task_id': self.task_id})
        try:
            path = os.path.join(self._conf['Terraform']['base_clone_path'],
                                self.task_id)
            self.create_dir(path)
            filters = [
                getattr(AutomationCode, 'name') == state,
                getattr(AutomationCode, 'cloud_provider') ==
                payload['cloud_provider']
            ]
            code = session.query(AutomationCode).filter(*filters).one()
            _creds = session.query(Credentials).filter(Credentials.id == code.cred_id).one()
            password = self.decrypt_password(_creds.password)
            self.clone_via_subprocess(
                subdir=path,
                token=password,
                repourl=code.repo_url,
                branch=code.branch
            )
            LOG.debug(f'cloning repository complete!', {'task_id': self.task_id})
            LOG.debug("Changing current working directory:%s" % code.script_path,
                      {'task_id': self.task_id})
            working_dir = os.path.join(path, code.script_path, 'data')
            self.change_dir(working_dir)
            LOG.debug("Changing current working directory:%s" % working_dir,
                      {'task_id': self.task_id})
            # Update main.tf file for import resource
            file_path = os.path.join(working_dir, 'main.tf')
            added_str = ""
            for i in range(len(ids)):
                added_str += "resource \"%s\" \"%s%s\" {}" % \
                             (IMPORT_RESOURCE_STR[payload.get('cloud_provider')][state],
                              state, i + 1)
                if len(ids) > 1:
                    added_str += "\n"
            LOG.debug("Added string:%s" % added_str, {'task_id': self.task_id})
            with open(file_path, "a") as f:
                f.write("\n")
                f.write(added_str)
            self.change_dir(working_dir)
            LOG.debug("Path and working dir:%s %s" % (path, working_dir),
                      {'task_id': self.task_id})
            return (path, working_dir,)
        except Exception as excp:
            raise excp

    def create_dir(self, path: str) -> None:
        LOG.debug("create_dir:%s" % path, {'task_id': self.task_id})
        try:
            if os.path.exists(path):
                self.destroy_dir(path)
            os.mkdir(path)
        except FileExistsError as excp:
            raise Exception

    def destroy_dir(self, path: str) -> None:
        LOG.debug("destroy_dir:%s" % path, {'task_id': self.task_id})
        try:
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(path)
        except FileNotFoundError as excp:
            raise Exception(excp)

    def change_dir(self, path: str) -> None:
        LOG.debug("change_dir:%s" % path, {'task_id': self.task_id})
        try:
            os.chdir(path)
        except FileNotFoundError as excp:
            raise excp

    def tf_init(self, backend_config: dict, **kwargs):
        LOG.debug("tf_init:%s" % backend_config, {'task_id': self.task_id})
        err_code, stdout, stderr = self.tf_obj.init(backend_config=backend_config)
        if err_code == 1:
            raise Exception(stderr)
        else:
            return stdout

    def _tfplan(self, **kwargs):
        LOG.debug(f'Creating terraform plan', {'task_id': self.task_id})
        global_opts = {'-chdir': kwargs['working_dir']}
        _tf = TerraformWrapper(
            global_opts=global_opts
        )
        opts = {'-detailed-exitcode': 'flagvalue'}
        err_code, stdout, stderr = _tf.plan(opts=opts, suppress=True)

        if err_code == 1:
            self.add_audit_log("Terraform", "TerraformPlan",
                               f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.FAILED)
            raise TerraformPlanException(stderr)
        else:
            self.add_audit_log("Terraform", "TerraformPlan",
                               f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.COMPLETED)
            return stdout


    def tf_set_workspace(self, identifier: str, **kwargs):
        LOG.debug(f'Creating terraform workspace[{identifier}]',
                           {'task_id': self.task_id})
        opts = {identifier: 'flagvalue'}
        err_code, stdout, stderr = self.tf_obj.set_workspace(identifier)
        if err_code == 1:
            self.add_audit_log('Terraform', 'SetTerraformWorkspace',
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.FAILED
            )
            raise TerraformCreateWorkspaceException(stderr)
        else:
            self.add_audit_log('Terraform', 'SetTerraformWorkspace',
                f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.COMPLETED
            )
            return stdout

    def tf_create_workspace(self, identifier: str, **kwargs):
        LOG.debug("tf_create_workspace:%s" % identifier, {'task_id': self.task_id})
        err_code, stdout, stderr = self.tf_obj.create_workspace(identifier)
        if err_code == 1:
            if "already exists" in stderr:
                return stdout
            raise Exception(stderr)
        else:
            return stdout

    def generate_infracost(self, session, _path: str, **kwargs):
        LOG.debug('get_infracost:%s' % _path,
                  {'task_id': self.task_id})
        _tf = TerraformWrapper()
        cost_json_filename = '{}_cost.json'.format(self.task_id)

        if os.path.exists(cost_json_filename):
            os.remove(os.path.join(_path, cost_json_filename))

        _opts = {'--terraform-use-state': 'flagvalue', '--path': '_path', '--format': 'json', '--out-file': cost_json_filename}
        err_code, stdout, stderr = _tf.infracost(opts=_opts, suppress=True)

        if err_code == 1:
            self.add_audit_log("Infracost", 'Infracost Generated',
                               f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.FAILED
                               )
            return 0
        else:
            self.add_audit_log("Infracost", 'Infracost Generated',
                               f'stderr[{stderr}] | stdout[{stdout}]', TASK_STATUS.COMPLETED
                               )
            f = open('{}/{}_cost.json'.format(_path, self.task_id), "r")
            cost_json = json.loads(f.read())

            try:
                with session:
                    _infracost = session.query(Infracost). \
                        where(Infracost.task_id.__eq__('{}_{}'.format(self.task_id, kwargs['state']))).one()
                    if _infracost > 0:
                        payload = {
                            "id": _infracost.id,
                            "task_id": _infracost.task_id,
                            "cost_json": cost_json
                        }
                    else:
                        payload = {
                            "task_id": '{}_{}'.format(self.task_id, kwargs['state']),
                            "cost_json": cost_json
                        }
            except sqexcp.NoResultFound as ex:
                payload = {
                    "task_id": '{}_{}'.format(self.task_id, kwargs['state']),
                    "cost_json": cost_json
                }
            LOG.debug("Insert infracost logs:%s" % payload, {'task_id': self.task_id})
            insert_infracost(payload, session_factory=self._db_conn._session_factory)
            self.add_audit_log('Infracost', 'Infracost Saved',
                               'Success', TASK_STATUS.COMPLETED
                               )
            return cost_json

    def tf_cmd(self, payload, state, ids):
        LOG.debug("tf_cmd:%s" % state, {'task_id': self.task_id})
        for i in range(len(ids)):
            resource_id = ids[i]
            self.add_audit_log("Terraform", "Import resource:%s" % resource_id,
                               "Started", TASK_STATUS.COMPLETED)
            resource_string = "%s.%s%s" % \
                              (IMPORT_RESOURCE_STR[payload.get('cloud_provider')][state],
                               state, i + 1)
            LOG.debug("Importing existing resource started:{} {}".format(resource_string, resource_id))
            err_code, stdout, stderr = self.tf_obj.cmd("import", resource_string,
                                                       resource_id)
            LOG.debug("Importing existing resource completed:{} {}".format(stdout, stdout))
            self.add_audit_log("Terraform", "Import resource:%s" % resource_id,
                               "Success", TASK_STATUS.COMPLETED)
            if err_code == 1:
                self.add_audit_log("Terraform", "Import resource:%s" % resource_id,
                                   "Failed", TASK_STATUS.FAILED)
                raise Exception(stderr)

    def tfpull_state(self):
        LOG.debug("tfpull_state", {'task_id': self.task_id})
        err_code, stdout, stderr = self.tf_obj.cmd("state pull")
        LOG.debug("Importing existing resource completed:{} {}".format(stdout, stdout))
        self.add_audit_log("Terraform", "Pull state started",
                           "Success", TASK_STATUS.COMPLETED)
        if err_code == 1:
            self.add_audit_log("Terraform", "Pull state started",
                               "Failed", TASK_STATUS.FAILED)
            raise Exception(stderr)

    def format_var(self, params: dict):
        upd_params = {}
        if 'use_remote_install' in params.keys() and params.get('software_installation_config'):
            upd_params = {k: {"value": v} for k, v in params['software_installation_config'].items()}
            upd_params_encode = (base64.b64encode(json.dumps(upd_params).encode())).decode("utf-8")
            params.update({'software_installation_config_b64': upd_params_encode})
        return params

    def create_tfvar(self, path: str, payload: dict, session=None, source=None):
        LOG.debug('create_tfvar:%s' % path, {'task_id': self.task_id})
        if os.path.exists(path) == True:
            return
        else:
            payload = self.format_var(payload)
            with open(path, 'w') as file:
                json.dump(payload, file)
            if "software_installation_config" in payload:
                ansible_file = path.replace("terraform.tfvars.json", "ansible_param.json")
                with open(ansible_file, 'w') as file:
                    json.dump(payload.get('software_installation_config'), file)
            return

    def create_askpass(self, path: str):
        path = os.path.join(path, 'askpass.py')
        if os.path.exists(path) == True:
            return
        else:
            with open(path, 'w') as file:
                file.write(ASKPASS_STR)
            os.chmod(path, stat.S_IRWXO)
            return

    def add_audit_log(self, source: str, event: str, trace: str, status: str):
        payload = {
            "task_id": self.task_id,
            "source": source,
            "event": event,
            "trace": trace,
            "status": status
        }
        LOG.debug("add_audit_log:%s" % payload, {'task_id': self.task_id})
        insert_audit_log(payload, session_factory=self._db_conn._session_factory)

    def __call__(self, state: str, payload: Dict[str, str], resource_ids: list, index: int):
        LOG.debug("Terraform call:%s" % payload, {'task_id': self.task_id})
        path = None
        try:
            with self._db_conn._session_factory() as session:
                state_name = "%s_%s_%s" % (self.task_id, state, index)
                state_model = get_states_model()
                try:
                    response = session.query(state_model).where(
                        state_model.name.__eq__(state_name)).one()
                    LOG.debug("State response is:%s" % response.name, {'task_id': self.task_id})

                    self.add_audit_log("Terraform", "import_resource",
                                       "Already imported", TASK_STATUS.COMPLETED)
                    return True
                except sqlalchemy.exc.NoResultFound:
                    LOG.debug("No state found in db", {'task_id': self.task_id})

                self.add_audit_log("Terraform", "import_resource",
                                   "started", TASK_STATUS.COMPLETED)
                if not os.path.exists(self._conf['Terraform']['base_clone_path']):
                    self.create_dir(self._conf['Terraform']['base_clone_path'])
                self.create_askpass(self._conf['Terraform']['base_clone_path'])
                path, working_dir = self.clone_repo(session, state, payload=payload,
                                                    ids=resource_ids)
                self.add_audit_log("Terraform", "clone_repo",
                                   "Success", TASK_STATUS.COMPLETED)

                LOG.debug(f'Generating terraform.tfvars.json file from request JSON!',
                                   {'task_id': self.task_id})
                self.create_tfvar(path=os.path.join(working_dir, "terraform.tfvars.json"),
                                  payload=payload)
                self.add_audit_log('Terraform', 'GenerateTFVars', "Success",
                                   TASK_STATUS.COMPLETED)

                if payload.get('cloud_provider') == 'gcp':
                    self.create_gcp_auth_file(path=os.path.join(working_dir, "auth_cred.json"),
                                              payload=payload, session=session, source=payload['source'])
                    self.add_audit_log("Terraform", 'GenerateGCPAuthFile', "Success",
                                       TASK_STATUS.COMPLETED)
                global_opts = {'-chdir': working_dir}
                self.tf_obj = Terraform(
                    working_dir=working_dir,
                    var_file=os.path.join(working_dir, "terraform.tfvars.json")
                )
                self.tf_init(backend_config=self._conf.get("terrafrom_init_backend_config"))
                self.add_audit_log("Terraform", "Terraform Init",
                                   "Success", TASK_STATUS.COMPLETED)
                self.tf_create_workspace(f'{self.task_id}_{state}_{index}')
                self.add_audit_log("Terraform", "Create workspace",
                                   "Success", TASK_STATUS.COMPLETED)
                self.tf_set_workspace(f'{self.task_id}_{state}_{index}')
                self.add_audit_log("Terraform", "Set workspace",
                                   "Success", TASK_STATUS.COMPLETED)
                self.tf_cmd(payload, state,
                            ids=resource_ids)
                #self.add_audit_log("Terraform", "import_resource",
                #                   "Success", TASK_STATUS.COMPLETED)
                #_plan = self._tfplan(
                #    task_id=payload['task_id'],
                #    state=state,
                #    working_dir=working_dir
                #)
                #self.tfpull_state()
                #self.add_audit_log("Terraform", "Pull state Completed",
                #                   "Success", TASK_STATUS.COMPLETED)
                #self.generate_infracost(session, working_dir,
                #                        task_id=payload['task_id'],
                #                        state=state)
                #self.add_audit_log("Terraform", 'InsertInfracost', "Success",
                #                   TASK_STATUS.COMPLETED)
                self.destroy_dir(path)
        except Exception as ex:
            if path:
                self.destroy_dir(path)
            self.add_audit_log("Terraform", "import_resource",
                               "%s" % str(ex), TASK_STATUS.FAILED)
            raise ex
