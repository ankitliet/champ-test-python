"""Repositories module."""
import logging

logger = logging.getLogger(__name__)

from sqlalchemy import exc as sqexcp


class CommonRepository:
    def __init__(self, session_factory, model) -> None:
        self.session_factory = session_factory
        self._model = model

    def fetch(self, iden_filters: dict):
        with self.session_factory() as session:
            try:
                filters = [getattr(self._model, column)
                           == value for column, value in iden_filters.items()]
                filter_query = session.query(self._model).filter(*filters)
                row = filter_query.one()
                return row
            except AttributeError as excp:
                raise Exception(f'Table[{self._model._str()}] has no column'
                                f'[{excp.__str__().split("attribute ", 1)[1]}]')
            except sqexcp.NoResultFound as excp:
                raise Exception(f'No record for table[{self._model._str()}] '
                                f'with applied filter[{iden_filters}]were found!')
            except sqexcp.MultipleResultsFound as excp:
                raise Exception(
                    f'Multiple records for table[{self._model._str()}] '
                    f'with applied filter[{iden_filters}] were found! Only one was required!'
                )

    def fetch_all(self, iden_filters: dict):
        with self.session_factory() as session:
            try:
                filters = [getattr(self._model, column)
                           == value for column, value in iden_filters.items()]
                filter_query = session.query(self._model).filter(*filters)
                rows = filter_query.all()
                return rows
            except sqexcp.NoResultFound as excp:
                raise Exception(f'No record for table[{self._model._str()}]'
                                f' with applied filter[{iden_filters}]were found!')
            except AttributeError as excp:
                raise Exception(f'Table[{self._model._str()}]'
                                f' has no column[{excp.__str__().split("attribute ", 1)[1]}]')

    def insert(self, **kwargs):
        with self.session_factory() as session:
            row = self._model(**kwargs)
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def upsert(self, iden_filters: dict, **kwargs):
        with self.session_factory() as session:
            if iden_filters:
                filters = [getattr(self._model, column)
                           == value for column, value in iden_filters.items()]
                try:
                    filter_query = session.query(self._model).filter(*filters)
                    row = filter_query.one()
                    if row:
                        for column, value in kwargs.items():
                            setattr(row, column, value)
                        session.add(row)
                        session.commit()
                        session.refresh(row)
                        return row
                except sqexcp.NoResultFound as excp:
                    pass
            row = self._model(**kwargs)
            session.add(row)
            session.commit()
            session.refresh(row)
            return row
