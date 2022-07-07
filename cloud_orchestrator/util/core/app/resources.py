"""Database module."""

from contextlib import contextmanager
from sqlalchemy import create_engine, orm
from sqlalchemy.orm import Session



class DatabaseResource:

    def __init__(self, db_url: str,db_schema:str) -> None:
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