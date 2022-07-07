"""Services module."""
import json

from .repositories import *



class CommonService:
    def __init__(self, repository: CommonRepository) -> None:
        self._repository = repository

    def get_session(self):
        return self._repository.get_session()

    def create_or_update(self, iden_filters: dict=None, **kwargs):
        return self._repository.upsert(iden_filters=iden_filters, **kwargs)

    def fetchlike_by_taskid(self, iden_filters: dict=None):
        return self._repository.fetchlike_by_taskid(iden_filters=iden_filters)

    def fetch(self, iden_filters):
        return self._repository.fetch(iden_filters=iden_filters)
    
    def fetch_all(self, iden_filters):
        return self._repository.fetch_all(iden_filters=iden_filters)
    
    def fetch_like(self, iden_filters):
        return self._repository.fetch_like(iden_filters=iden_filters)
    
    def state_trans_status(self, iden_filters):
        return self._repository.state_trans_status(iden_filters=iden_filters)
    
    def paginate_fetch(self,iden_filters,page,per_page,total):
        return self._repository.paginate_fetch(iden_filters=iden_filters,page=page,per_page=per_page,total = total)
    
    def delete(self, iden_filters):
        return self._repository.delete(iden_filters=iden_filters)
    
    def dashboard(self, starttime,endtime):
        return self._repository.dashboard(starttime = starttime,endtime = endtime)
    
    def get_identifier(self, iden_filters):
        return self._repository.get_identifier(iden_filters=iden_filters)
    
    def processor_insights(self, starttime,endtime):
        return self._repository.processor_insights(starttime = starttime,endtime = endtime)
    
    def references_search(self, iden_filters,page,per_page):
        return self._repository.references_search(iden_filters=iden_filters,page=page,per_page=per_page)