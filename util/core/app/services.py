from .repositories import CommonRepository

class CommonService:
    def __init__(self, repository: CommonRepository) -> None:
        self._repository = repository

    def create_or_update(self, iden_filters: dict=None, **kwargs):
        return self._repository.upsert(iden_filters=iden_filters, **kwargs)

    def create(self, **kwargs):
        return self._repository.insert(**kwargs)
    
    def fetch(self, iden_filters):
        return self._repository.fetch(iden_filters=iden_filters)
    
    def fetch_all(self, iden_filters):
        return self._repository.fetch_all(iden_filters=iden_filters)
