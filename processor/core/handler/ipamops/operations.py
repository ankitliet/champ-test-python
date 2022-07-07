from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS
from resource_adapters.providers.ipam.vmoperations import *

from util.core.app.logger import get_logger_func
LOG = get_logger_func(__file__)

class Operations:
    def __init__(self, session, task_id, config, env_vars):
        self.session = session
        self.task_id = task_id
        self.config = config
        self.env_vars = env_vars
        LOG.debug("IPAM Operation init method", {'task_id': self.task_id})

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

    def __call__(self, operation_name, parameters: dict):
        LOG.debug("IPAM Operation call:%s" % parameters, {'task_id': self.task_id})
        try:
            self.add_audit_log("IPAM Operation", operation_name,
                               "Started", TASK_STATUS.COMPLETED)
            eval(operation_name)(parameters, self.session,
                                 config=self.config,
                                 env_vars=self.env_vars)
            self.add_audit_log("IPAM Operation", operation_name,
                               "Success", TASK_STATUS.COMPLETED)
            return parameters
        except Exception as ex:
            raise Exception("Failed operation:%s" % str(ex))