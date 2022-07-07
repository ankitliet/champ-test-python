import json
from datetime import datetime
from copy import deepcopy

from .repositories import *



#GLOBALS
secrets = ['azure_client_secret', 'admin_password']


def recr_dict(tmp: dict):
    for key, value in tmp.items():
        if isinstance(value, dict):
            recr_dict(value)
        elif isinstance(value, list):
            recr_list(value)
        else:
            if key in secrets:
                tmp[key] = 'XXXX-SECRET-XXXX'

                    
def recr_list(tmp: list):
    for value in tmp:
        if isinstance(value, dict):
            recr_dict(value)
        elif isinstance(value, list):
            recr_list(value)
        else:
            if value in secrets:
                index = tmp.index(value)
                tmp.pop(index)
                tmp.insert(index, 'XXXX-SECRET-XXXX')





class CommonService:
    def __init__(self, repository: CommonRepository) -> None:
        self._repository = repository

    def insert_or_update(self, iden_filters: dict=None, **kwargs):
        return self._repository.upsert(iden_filters=iden_filters, **kwargs)
    
    def insert(self, **kwargs):
        return self._repository.insert(**kwargs)
    
    def update(self, iden_filters, **kwargs):
        return self._repository.update(iden_filters=iden_filters, **kwargs)
    
    def fetch(self, iden_filters):
        return self._repository.fetch(iden_filters=iden_filters)
    
    def fetch_all(self, iden_filters):
        return self._repository.fetch_all(iden_filters=iden_filters)
    
    


class StateTransitionLogService(CommonService):
    
    def insert(self, **kwargs):
#         kwargs = deepcopy(kwargs)
#         recr_dict(kwargs)
        return self._repository.insert(**kwargs)
    
    def insert_log(self, **kwargs):
#         kwargs = deepcopy(kwargs)
#         recr_dict(kwargs)
        kwargs.update({
            'created_timestamp': datetime.now()
        })
        return self._repository.insert(**kwargs)
        
    def update_log(self, task_id, **kwargs):
#         kwargs = deepcopy(kwargs)
#         recr_dict(kwargs)
        kwargs.update({
            'updated_timestamp': datetime.now()
        })
        return self._repository.update(iden_filters={'task_id': task_id}, **kwargs)
    
    
    
    
class AuditService(CommonService):
    
    def insert_audit(self, task_id: str, source: str, event: str, trace: str, status: str):
        self.create(
            task_id=task_id,
            source=source,
            event=event,
            trace=trace,
            status=status,
            timestamp=datetime.now()
        )