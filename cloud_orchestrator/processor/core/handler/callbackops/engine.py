'''
`engine.py` file
'''

# GENERATING LOGGER for `base`
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
from typing import Dict
import os
from util.core.app.constants import TASK_STATUS

from util.core.app.audit_log_transaction import insert_audit_log
from .callback import CallBack

class Engine:
    '''
    : `Engine` class that acts as a wrapper over all other utilities/features
    '''
    
    def __init__(self, **kwargs):
        self._logger = LOG # logger.getlogger(self.__class__.__name__)
        self._conf = kwargs['conf']
        self._db_conn = kwargs['db_conn']
        self._env_vars = kwargs['env_vars']
        LOG.debug("CallBack Engine:%s" % kwargs)
        #self._unset_proxy()

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

    def add_audit_log(self, task_id, source, event, trace, status):
        payload = {
            "task_id": task_id,
            "source": source,
            "event": event,
            "trace": trace,
            "status": status
        }
        LOG.debug("Insert audit logs:%s" % payload, {'task_id': task_id})
        insert_audit_log(payload, session_factory=self._db_conn._session_factory)

    def __call__(self, state: str, payload: Dict[str, str], autoinitiate: bool):
        task_id = payload.get('task_id', 'NA')
        self._logger.debug('Executing callback operation:%s' % payload,
                           {'task_id': task_id})
        try:

            self.add_audit_log(payload["task_id"], "Callback Engine", "Initialize",
                               "Success", TASK_STATUS.COMPLETED)
            #self._unset_proxy()
            if not payload['parameters'].get('test_run', False):
                self._logger.debug('Executing callback operations')
                operation_obj = CallBack(session=self._db_conn,
                                         task_id=payload.get("task_id"),
                                         config=self._conf,
                                         env_vars=self._env_vars)
                operation_obj(payload)
            self.add_audit_log(payload.get("task_id"), "Callback Engine", state,
                               "Success", TASK_STATUS.COMPLETED)
            #self._set_proxy()
            return (payload, 'success',)
        except Exception as excp:
            self._logger.exception(excp, {'task_id': task_id})
            self.add_audit_log(payload["task_id"], "Callback Engine",
                               state, excp.__str__(), TASK_STATUS.FAILED)
            raise excp
        # finally:
        #     self._unset_proxy()