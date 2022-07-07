'''
`engine.py` file
'''

from util.core.app.logger import get_logger_func
LOG = get_logger_func(__file__)

'''
: External Imports
    : os
    : sqlalchemy.orm.Session
    : python_terraform
'''
from typing import Dict
from util.core.app.constants import TASK_STATUS

from util.core.app.audit_log_transaction import insert_audit_log
from .operations import Operations

class Engine:
    '''
    : `Engine` class that acts as a wrapper over all other utilities/features
    '''
    
    def __init__(self, **kwargs):
        self._logger = LOG # logger.getlogger(self.__class__.__name__)
        self._conf = kwargs['conf']
        self._db_conn = kwargs['db_conn']
        self._env_vars = kwargs['env_vars']
        LOG.debug("Azure Operation init:%s" % kwargs)

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
        try:
            # Create an object of vm operation class and perform operation
            self._logger.debug('Executing Azure operation:%s' % payload,
                               {'task_id': task_id})
            self.add_audit_log(payload["task_id"], state, "Initialize",
                               "Success", TASK_STATUS.COMPLETED)
            if not payload['parameters'].get('test_run', False):
                self._logger.debug('Executing vm operation')
                operation_obj = Operations(
                    session=self._db_conn, task_id=payload.get("task_id"),
                    config=self._conf, env_vars=self._env_vars)
                parameters = payload.get('parameters')
                parameters['source'] = payload.get('source')
                parameters['task_id'] = payload.get('task_id')
                operation_obj(state, parameters)

            self.add_audit_log(payload.get("task_id"), state, state,
                               "Success", TASK_STATUS.COMPLETED)
            return (payload, 'success',)
        except Exception as excp:
            self._logger.exception(excp, {'task_id': task_id})
            self.add_audit_log(payload["task_id"], state,
                               state, excp.__str__(), TASK_STATUS.FAILED)
            raise excp