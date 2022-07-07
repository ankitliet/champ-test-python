import os
import sqlalchemy.exc
import base64
import json
import time

from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from util.core.app.email_client import send_email
from util.core.app.models import Application as CallbackApplication
import requests

# from .logger import getlogger
# logger = getlogger(__file__)

from util.core.app.logger import get_logger_func
LOG = get_logger_func(__file__)

#GLOBALS
BASE_DESC = '''
Dear Team:
<br>
<br>
Cloud Orch Execution for Transaction ID {} is FAILED. Please check the below transaction details and update the customer. If you have subscribed for AzureDevOps, ticket has been opened for the failure transaction for tracking purpose.
<br>
<br>
Admin UI: <b> {} </b>
<br>
task_id: <b> {} </b>
<br>
cloud_provider: {}
<br>
task_name: {}
<br>
Source: HCMP
<br>
references: {}
<br>
Status: <b> {} </b>
<br>
Message: {}
<br>
<br>

Thanks & Regards
Cloud Orchestrator Automation Team
'''

def create_work_item(uri: str, title: str, description: str, token: str, verify: bool=False):
    data = [
        {
            "op": "add",
            "path": "/fields/System.Title",
            "value": title
        },
        {
            "op": "add",
            "path": "/fields/System.Description",
            "value": description
        }
    ]
    resp = requests.post(
        uri, json=data,
        headers={'Content-Type': 'application/json-patch+json'},
        auth=('', token),
        verify=verify
    )
    resp.raise_for_status()
    return resp.json()



class CallBack:

    no_proxies = {
          "http": None,
          "https": None,
        }

    def __init__(self, session, task_id, config, env_vars):
        self._logger = LOG # logger.getlogger(self.__class__.__name__)
        self.session = session
        self.task_id = task_id
        self.config = config
        self.api_url = "%s%s" % (config.get('ORCH').get('api_url'), task_id)
        self.admin_url = "%s%s" % (config.get('ORCH').get('admin_url'), task_id)
        self.env_vars = env_vars
        LOG.debug("Callback init method", {'task_id': self.task_id})


    def _set_proxy(self):
        if os.environ.get('PROXY_ENABLED', 'False') == 'True':
            self._logger.debug(f'setting proxy[http_proxy:{self.env_vars.get("http_proxy")}]')
            self._logger.debug(f'setting proxy[https_proxy:{self.env_vars.get("https_proxy")}]')
            os.environ['http_proxy'] = self.env_vars.get('http_proxy')
            os.environ['https_proxy'] = self.env_vars.get('https_proxy')

    def _unset_proxy(self):
        self._logger.debug('Unsetting proxy!')
        os.environ['http_proxy'] = ''
        os.environ['https_proxy'] = ''

    def add_audit_log(self, source, event, trace, status):
        payload = {
            "task_id": self.task_id,
            "source": source,
            "event": event,
            "trace": trace,
            "status": status
        }
        LOG.debug("Insert audit logs:%s" % payload, {'task_id': self.task_id})
        insert_audit_log(payload, session_factory=self.session._session_factory)

    def get_api_response(self, retry_count=3):
        """
        :param retry_count: No of times retry api
        :return: response
        """
        for i in range(retry_count):
            self._logger.debug("calling application url......", {'task_id': self.task_id, 'api_url': self.api_url})
            response = requests.get(self.api_url, verify=False)
            if response.status_code == 200 or response.status_code == 403\
                    or response.status_code == 404:
                return response
            if i == (retry_count - 1):
                return response
            self._logger.debug("Sleeping for 2 sec......", {'task_id': self.task_id})
            time.sleep(2)

    def __call__(self, parameters):
        self.add_audit_log("Callback",
                           "call_back_operation",
                           "started", TASK_STATUS.COMPLETED)
        self._logger.debug("Parameters are:%s" % parameters, {'task_id': self.task_id})
        # Fetch the task_id response
        # self._unset_proxy()
        response = self.get_api_response()
        self.add_audit_log("Callback task response:%s" % self.api_url,
                           "call_back_operation:%s" % response.status_code,
                           "Success", TASK_STATUS.COMPLETED)

        if response.status_code == 200:
            self._logger.debug("Response is:%s" % response.json(), {'task_id': self.task_id})
            data = response.json()
            payload = json.dumps(data)
            self._logger.debug("Task Response is:%s" % payload, {'task_id': self.task_id})
            try:
                callback_channels = self.session._session_factory().query(
                    CallbackApplication).where(
                    CallbackApplication.is_active.__eq__(True)).where(
                    CallbackApplication.source.__eq__(parameters.get('source'))).order_by(
                    CallbackApplication.created_date.desc()).one()
                self._logger.debug("Channels are:%s" % callback_channels.channel,
                                   {'task_id': self.task_id})
                webhooks_channels = callback_channels.channel.get('channel').get('webhook')
                email_channel = callback_channels.channel.get('channel').get('email')
                devops_channel = callback_channels.channel.get('channel').get('devops')
            except sqlalchemy.exc.NoResultFound as ex:
                self.add_audit_log("Callback",
                                   "call_back_operation:%s" % "No callback application configured",
                                   "%s" % str(ex), TASK_STATUS.FAILED)
                webhooks_channels = []
                email_channel = {}
                devops_channel = {}
            channel_type = ""
            webhook_details = {}
            if webhooks_channels:
                for channel in webhooks_channels:
                    webhook_details[channel.get("type")] = channel
            try:
                callback_info = parameters.get('parameters').get("callback_info")
                if callback_info:
                    webhook_details[callback_info['type']] = callback_info
                self._logger.debug("Webhook channels are:%s" % webhooks_channels,
                                   {'task_id': self.task_id})
                self._logger.debug("Email channel is:%s" % email_channel,
                                   {'task_id': self.task_id})
                self._logger.debug("Devops channel is:%s" % devops_channel,
                                   {'task_id': self.task_id})
                try:
                    for channel_type, channel in webhook_details.items():
                        source = channel.get("url")
                        secret_key = channel.get("secret_key")
                        access_key = channel.get("access_key")
                        self.add_audit_log("Callback:%s" % channel_type,
                                           "call_back_operation:%s" % source,
                                           "Started", TASK_STATUS.COMPLETED)
                        if not source:
                            self.add_audit_log("Callback:%s" % channel_type,
                                               "Source missing for callback",
                                               "Failed", TASK_STATUS.FAILED)
                            continue
                        if access_key and secret_key:
                            credentials = {secret_key: access_key,
                                           "interface_type": "rest"}
                            b64_str = str(credentials)
                            b64_str = b64_str.replace("'", "\"")
                            string_bytes = b64_str.encode("ascii")
                            base64_bytes = base64.b64encode(string_bytes)
                            base64_string = base64_bytes.decode("ascii")
                            headers = {'credentials': base64_string}
                            res = requests.post(source, data=payload, headers=headers, verify=False)
                        else:
                            res = requests.post(source, data=payload, verify=False)
                        if res.status_code == 200:
                            message = "Status:%d, Message:%s" % (res.status_code, res.json())
                            self.add_audit_log("Callback:%s" % channel_type,
                                               "call_back_operation:%s" % message,
                                               "Success", TASK_STATUS.COMPLETED)
                        else:
                            message = "Status:%d" % res.status_code
                            self.add_audit_log("Callback:%s" % channel_type,
                                               "call_back_operation:%s" % message,
                                               "Failed", TASK_STATUS.FAILED)
                except Exception as excp:
                    self._logger.exception(excp, {'task_id': self.task_id})
                    self.add_audit_log("Callback:%s" % channel_type,
                                       "call_back_operation",
                                       "%s" % str(excp), TASK_STATUS.FAILED)
                try:
                    if email_channel:
                        channel_type = "Email"
                        if email_channel.get('host') and email_channel.get('from_addr') \
                                and email_channel.get('to_addr'):
                            self.add_audit_log("Callback:Email",
                                               "call_back_operation",
                                               "Started", TASK_STATUS.COMPLETED)
                            self._logger.debug("Data is:%s" % data,
                                               {'task_id': self.task_id})
                            kwargs = {
                                "api_url": self.admin_url,
                                "task_id": self.task_id,
                                "task_name": data.get('details').get('task_name'),
                                "source": parameters.get('source'),
                                "references": data.get('details').get("references"),
                                "cloud_provider": data.get('details').get("cloud_provider"),
                                "status": data.get("status"),
                                "created_by": parameters.get('created_by', "NA"),
                                "modified_by": parameters.get('modified_by', "NA"),
                                "message": data.get("message")
                            }
                            send_email(email_channel.get('host'), email_channel.get('port', 25),
                                       email_channel.get('from_addr'), email_channel.get('to_addr'),
                                       **kwargs)
                            self.add_audit_log("Callback:Email",
                                               "call_back_operation",
                                               "Success", TASK_STATUS.COMPLETED)
                        else:
                            self.add_audit_log("Callback:Email",
                                               "call_back_operation:Missing configuration",
                                               "Failed", TASK_STATUS.FAILED)
                except Exception as excp:
                    self._logger.exception(excp, {'task_id': self.task_id})
                    self.add_audit_log("Callback:%s" % channel_type,
                                       "call_back_operation",
                                       "%s" % str(excp), TASK_STATUS.FAILED)
                if response.json().get('status', '').lower() == 'failed':
                    try:
                        if devops_channel == None:
                            self._logger.debug("Devops channel info is missing", {'task_id': self.task_id})
                        else:
                            self.add_audit_log("Callback:DevOps",
                                                   "call_back_operation",
                                                   "Started", TASK_STATUS.COMPLETED)
                            dev_resp = create_work_item(
                                uri=devops_channel.get('uri'),
                                title = f'{self.task_id} [FAILED]',
                                token=devops_channel.get('token'),
                                description=BASE_DESC.format(
                                    self.task_id, self.admin_url, self.task_id, data.get('details').get("cloud_provider"),
                                    data.get('details').get('task_name'), data.get('details').get("references"),
                                    data.get("status"), data.get("message"),
                                )
                            )
                            self.add_audit_log("Callback:DevOps",
                                                   "call_back_operation",
                                                  str(dev_resp.get('id', '')), TASK_STATUS.COMPLETED)
                    except Exception as ex:
                        self._logger.exception(ex, {'task_id': self.task_id})
                        self.add_audit_log("Callback:DevOps",
                                           "call_back_operation",
                                           "%s" % str(ex), TASK_STATUS.FAILED)
            except Exception as exc:
                self._logger.exception(exc, {'task_id': self.task_id})
                self.add_audit_log("Callback:%s" % channel_type,
                                   "call_back_operation",
                                   "%s" % str(exc), TASK_STATUS.FAILED)
        else:
            self._logger.debug("Response is:%s" % response.status_code,
                               {'task_id': self.task_id})
            self.add_audit_log("Callback",
                               "Failed to get response, status code:%s" % response.status_code,
                               "Failed", TASK_STATUS.FAILED)
        self.add_audit_log("Callback",
                           "call_back_operation",
                           "Success", TASK_STATUS.COMPLETED)
        return (parameters, 'success',)