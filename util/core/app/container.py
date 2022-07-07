from dependency_injector import containers, providers

from .repositories import CommonRepository
from .resources import DatabaseResource
from .services import CommonService
from .models import TransactionLog


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    db = providers.Singleton(
        DatabaseResource,
        db_url=config.DatabaseResource.uri,
        db_schema=config.DatabaseResource.schema
    )

    audit_repository = providers.Factory(
        CommonRepository,
        session_factory=db.provided.session,
        model=TransactionLog
    )

    audit_service = providers.Factory(
        CommonService,
        repository=audit_repository
    )