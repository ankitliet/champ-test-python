# TODO
# 1. comments and typing hints

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Executor
from dependency_injector.wiring import inject, Provide
from dependency_injector import resources
from sqlalchemy import create_engine, orm
from sqlalchemy.orm import Session
from contextlib import contextmanager
from typing import Tuple
import grpc
from py_grpc_prometheus.prometheus_server_interceptor import PromServerInterceptor
from prometheus_client import start_http_server


class ThreadExecutorResource(resources.Resource):

    @inject
    def init(
            self,
            max_workers: int = Provide['manager.threadexecutor.max_workers'],
            thread_name_prefix: str = Provide['manager.threadexecutor.thread_name_prefix'],
            initializer=Provide['manager.threadexecutor.initializer'],
            initargs: Tuple = Provide['manager.threadexecutor.initargs'],
            grpc_http_port=Provide['manager.threadexecutor.grpc_port'],
    ) -> Executor:
        thread_pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix,
            initializer=initializer,
            initargs=initargs
        )
        server = grpc.server(thread_pool,
                             interceptors=(PromServerInterceptor(enable_handling_time_histogram=True, legacy=True),))
        server.start()
        # Start an end point to expose metrics.
        start_http_server(9090)

        return thread_pool

    @inject
    def shutdown(
            self, resource: Executor, wait: bool = Provide['manager.threadexecutor.wait'],
            cancel_futures: bool = Provide['manager.threadexecutor.cancel_futures']
    ) -> None:
        resource.shutdown(
            wait=wait,
            cancel_futures=False
        )


class DatabaseResource:

    def __init__(self, db_url: str, db_schema: str) -> None:
        self._engine = create_engine(
            db_url, pool_size=20, max_overflow=15, echo=False,
            pool_recycle=300, pool_pre_ping=True, pool_use_lifo=True,
            connect_args={'options': '-csearch_path={}'.format(db_schema)}
        )
        self._session_factory = orm.scoped_session(
            orm.sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine,
            ),
        )

    @contextmanager
    def session(self):
        session: Session = self._session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            # session.remove()
