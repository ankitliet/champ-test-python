"""Repositories module."""
from typing import Iterator
from sqlalchemy import exc as sqexcp
from uuid import uuid4 as uuid
from sqlalchemy import func, case, desc, distinct
from sqlalchemy import and_
from util.core.app.models import *
from sqlalchemy_paginator import Paginator
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class CommonRepository:
    """
        class funtion return repos related data
    """
    def __init__(self, session_factory, model) -> None:
        self.session_factory = session_factory
        self._model = model

    def get_session(self):
        """
            function to return factory session
        """
        return self.session_factory

    def fetchlike_by_taskid(self, iden_filters: dict):
        """
            function to return taskid related data
        """
        with self.session_factory() as session:
            try:
                task_id = iden_filters.get('task_id')
                search = "{}%".format(task_id)
                filter_query = session.query(self._model).filter(self._model.task_id.like(search))
                rows = filter_query.all()
                return rows
            except AttributeError as excp:
                raise Exception(
                    f'Table[{self._model._str()}] has no column[{excp.__str__().split("attribute ", 1)[1]}]')
            except sqexcp.NoResultFound as excp:
                raise Exception(
                    f'No record for table[{self._model._str()}] with applied filter[{iden_filters}]were found!')
            except sqexcp.MultipleResultsFound as excp:
                raise Exception(
                    f'Multiple records for table[{self._model._str()}] with applied filter[{iden_filters}] were found! Only one was required!'
                )

    def fetch(self, iden_filters: dict):
        with self.session_factory() as session:
            try:
                filters = [getattr(self._model, column) == value for column, value in iden_filters.items()]
                filter_query = session.query(self._model).filter(*filters)
                row = filter_query.one()
                return row
            except AttributeError as excp:
                raise Exception(
                    f'Table[{self._model._str()}] has no column[{excp.__str__().split("attribute ", 1)[1]}]')
            except sqexcp.NoResultFound as excp:
                raise Exception(
                    f'No record for table[{self._model._str()}] with applied filter[{iden_filters}]were found!')
            except sqexcp.MultipleResultsFound as excp:
                raise Exception(
                    f'Multiple records for table[{self._model._str()}] with applied filter[{iden_filters}] were found! Only one was required!'
                )

    def fetch_all(self, iden_filters: dict):
        with self.session_factory() as session:
            try:
                starttime = None
                endtime = None
                if 'starttime' in iden_filters:
                    starttime = iden_filters['starttime']
                    iden_filters.pop('starttime')

                if 'endtime' in iden_filters:
                    endtime = iden_filters['endtime']
                    iden_filters.pop('endtime')

                refs = {}
                parameters = {}

                if 'references' in iden_filters and self._model._str() == 'automation_request':
                    refs = iden_filters['references']
                    del iden_filters['references']

                if 'parameters' in iden_filters and self._model._str() == 'automation_request':
                    parameters = iden_filters['parameters']
                    del iden_filters['parameters']

                filters = [getattr(self._model, column) == value for column, value in iden_filters.items()]

                if self._model._str() == 'automation_request':
                    for column, value in refs.items():
                        if isinstance(value, int):
                            filters.append(self._model.references[column].astext.cast(Integer) == value)
                        elif isinstance(value, str):
                            filters.append(self._model.references[column].astext == value)

                if self._model._str() == 'automation_request':
                    for column, value in parameters.items():
                        if isinstance(value, int):
                            filters.append(self._model.parameters[column].astext.cast(Integer) == value)
                        elif isinstance(value, str):
                            filters.append(self._model.parameters[column].astext == value)

                if starttime is not None:
                    filters.append(getattr(self._model, 'created_date') >= starttime)
                if endtime is not None:
                    filters.append(getattr(self._model, 'created_date') <= endtime)
                filter_query = session.query(self._model).filter(*filters)
                if self._model._str() == 'state_transition_log':
                    filter_query = filter_query.order_by(self._model.created_timestamp.desc())
                elif self._model._str() == 'transaction_log_audit':
                    filter_query = filter_query.order_by(self._model.timestamp.desc())
                elif self._model._str() == 'states' or self._model._str() == 'credentials':
                    filter_query = filter_query
                elif self._model._str() == 'automation_request':
                    filter_query = filter_query.order_by(self._model.created_date.desc())
                elif self._model._str() == 'queues':
                    filter_query = filter_query
                elif self._model._str() == 'resource_adapter_mapping':
                    filter_query = filter_query
                elif self._model._str() == 'task_config':
                    filter_query = filter_query
                elif self._model._str() == 'api_configurations':
                    filter_query = filter_query
                elif self._model._str() == 'product_category':
                    filter_query = filter_query
                elif self._model._str() == 'product_subcategory':
                    filter_query = filter_query
                elif self._model._str() == 'product_items':
                    filter_query = filter_query
                else:
                    filter_query = filter_query.order_by(self._model.created_date.desc())

                rows = filter_query.all()
                return rows
            except sqexcp.NoResultFound as excp:
                raise Exception(
                    f'No record for table[{self._model._str()}] with applied filter[{iden_filters}]were found!')
            except AttributeError as excp:
                raise Exception(
                    f'Table[{self._model._str()}] has no column[{excp.__str__().split("attribute ", 1)[1]}]')

    def dashboard(self, starttime, endtime):
        with self.session_factory() as session:
            try:
                filters = []
                filters.append(getattr(self._model, 'created_date') >= starttime)
                filters.append(getattr(self._model, 'created_date') < endtime)
                response = session.query(
                    func.coalesce(func.count(), 0).label('total'),
                    func.coalesce(func.sum(case([((self._model.status == 'SUCCESS'), 1)], else_=0)), 0).label(
                        'success'),
                    func.coalesce(func.sum(case([((self._model.status == 'FAILED'), 1)], else_=0)), 0).label('failure'),
                    func.coalesce(func.sum(case([((self._model.status == 'IN_PROGRESS'), 1)], else_=0)), 0).label(
                        'in_progress'),
                    func.coalesce(func.sum(case([((self._model.status == 'IN_QUEUE'), 1)], else_=0)), 0).label(
                        'in_queue')
                ).filter(*filters
                         ).all()
                resp = session.query(
                    self._model.cloud_provider.label('cloud_provider'),
                    func.coalesce(func.count(), 0).label('total'),
                    func.coalesce(func.sum(case([((self._model.status == 'SUCCESS'), 1)], else_=0)), 0).label(
                        'success'),
                    func.coalesce(func.sum(case([((self._model.status == 'FAILED'), 1)], else_=0)), 0).label('failure'),
                    func.coalesce(func.sum(case([((self._model.status == 'IN_PROGRESS'), 1)], else_=0)), 0).label(
                        'in_progress'),
                    func.coalesce(func.sum(case([((self._model.status == 'IN_QUEUE'), 1)], else_=0)), 0).label(
                        'in_queue')
                ).filter(*filters
                         ).group_by(self._model.cloud_provider
                                    ).all()
                response = response[0]
                resp1 = session.query(
                    self._model.cloud_provider.label('cloud_provider'),
                    self._model.task_name.label('task_name'),
                    func.count().label('count'),
                ).filter(*filters
                         ).group_by(self._model.task_name, self._model.cloud_provider
                                    ).order_by(desc('count')
                                               ).all()

                response = {'total': response[0], 'success': response[1], 'failure': response[2],
                            'in_progress': response[3], 'in_queue': response[4]}

                for x in resp:
                    cp = x[0]
                    val = {'total': x[1], 'success': x[2], 'failure': x[3], 'in_progress': x[4], 'in_queue': x[5]}
                    response[cp] = val
                    response[cp]['top_10_tasks'] = []

                for x in resp1:
                    cp = x[0]
                    task = x[1]
                    if len(response[cp]['top_10_tasks']) < 10:
                        response[cp]['top_10_tasks'].append({task: x[2]})

                processor_ins = session.query(
                    AutomationRequest.status, StateTransitionLog.identifier, AutomationRequest.task_id,
                    func.min(StateTransitionLog.created_timestamp), AutomationRequest.cloud_provider
                ).select_from(AutomationRequest
                              ).join(StateTransitionLog, and_(AutomationRequest.task_id == StateTransitionLog.plan_id)
                                     ).filter(*filters
                                              ).group_by(AutomationRequest.status, StateTransitionLog.identifier,
                                                         AutomationRequest.task_id, AutomationRequest.cloud_provider
                                                         ).all()
                # print(processor_ins)
                df = pd.DataFrame(processor_ins,
                                  columns=['status', 'identifier', 'task_id', 'timestamp', 'cloud_provider'])
                df = df.sort_values('timestamp')
                df = df.drop_duplicates(subset="task_id", keep='first')
                df = df.groupby(['identifier', 'status', 'cloud_provider']).count()
                df = df.to_dict()
                df = df['task_id']
                processor = {}
                for k, v in df.items():
                    if k[0] in processor:
                        if k[2] in processor[k[0]]:
                            processor[k[0]][k[2]][k[1]] = v
                        else:
                            processor[k[0]][k[2]] = {k[1]: v}
                    else:
                        processor[k[0]] = {k[2]: {k[1]: v}}

                # print(processor)
                response['processor_insights'] = processor
                return response
            except sqexcp.NoResultFound as excp:
                raise Exception(
                    f'No record for table[{self._model._str()}] with applied filter[{iden_filters}]were found!')
            except AttributeError as excp:
                raise Exception(
                    f'Table[{self._model._str()}] has no column[{excp.__str__().split("attribute ", 1)[1]}]')

    def processor_insights(self, starttime, endtime):
        with self.session_factory() as session:
            try:
                response = {}
                filters = []
                filters.append(getattr(self._model, 'created_date') >= starttime)
                filters.append(getattr(self._model, 'created_date') < endtime)
                processor_ins = session.query(
                    AutomationRequest.status, StateTransitionLog.identifier, AutomationRequest.task_id,
                    func.min(StateTransitionLog.created_timestamp), AutomationRequest.cloud_provider
                ).select_from(AutomationRequest
                              ).join(StateTransitionLog, and_(AutomationRequest.task_id == StateTransitionLog.plan_id)
                                     ).filter(*filters
                                              ).group_by(AutomationRequest.status, StateTransitionLog.identifier,
                                                         AutomationRequest.task_id, AutomationRequest.cloud_provider
                                                         ).all()
                # print(processor_ins)
                df = pd.DataFrame(processor_ins,
                                  columns=['status', 'identifier', 'task_id', 'timestamp', 'cloud_provider'])
                df = df.sort_values('timestamp')
                df = df.drop_duplicates(subset="task_id", keep='first')
                df = df.groupby(['identifier', 'status', 'cloud_provider']).count()
                df = df.to_dict()
                df = df['task_id']
                processor = {}
                for k, v in df.items():
                    if k[0] in processor:
                        if k[2] in processor[k[0]]:
                            processor[k[0]][k[2]][k[1]] = v
                        else:
                            processor[k[0]][k[2]] = {k[1]: v}
                    else:
                        processor[k[0]] = {k[2]: {k[1]: v}}

                # print(processor)
                response['processor_insights'] = processor
                return response
            except sqexcp.NoResultFound as excp:
                raise Exception(
                    f'No record for table[{self._model._str()}] with applied filter[{iden_filters}]were found!')
            except AttributeError as excp:
                raise Exception(
                    f'Table[{self._model._str()}] has no column[{excp.__str__().split("attribute ", 1)[1]}]')

    def upsert(self, iden_filters: dict, **kwargs):
        with self.session_factory() as session:
            if iden_filters:
                filters = [getattr(self._model, column) == value for column, value in iden_filters.items()]
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

    def fetch_like(self, iden_filters: dict):
        with self.session_factory() as session:
            try:
                task_id = iden_filters.get('task_id')
                search = "{}%".format(task_id)
                filter_query = session.query(self._model).filter(self._model.name.like(search))
                rows = filter_query.all()
                return rows
            except sqexcp.NoResultFound as excp:
                raise Exception(
                    f'No record for table[{self._model._str()}] with applied filter[{iden_filters}]were found!')
            except AttributeError as excp:
                raise Exception(
                    f'Table[{self._model._str()}] has no column[{excp.__str__().split("attribute ", 1)[1]}]')

    def paginate_fetch(self, iden_filters, per_page, page, total):
        with self.session_factory() as session:
            try:
                starttime = None
                endtime = None
                if 'starttime' in iden_filters:
                    starttime = iden_filters['starttime']
                    iden_filters.pop('starttime')

                if 'endtime' in iden_filters:
                    endtime = iden_filters['endtime']
                    iden_filters.pop('endtime')

                refs = {}

                parameters = {}

                if 'references' in iden_filters and self._model._str() == 'automation_request':
                    refs = iden_filters['references']
                    del iden_filters['references']

                if 'parameters' in iden_filters and self._model._str() == 'automation_request':
                    parameters = iden_filters['parameters']
                    del iden_filters['parameters']

                filters = [getattr(self._model, column) == value for column, value in iden_filters.items()]

                if self._model._str() == 'automation_request':
                    for column, value in refs.items():
                        if isinstance(value, int):
                            filters.append(self._model.references[column].astext.cast(Integer) == value)
                        elif isinstance(value, str):
                            filters.append(self._model.references[column].astext == value)

                if self._model._str() == 'automation_request':
                    for column, value in parameters.items():
                        if isinstance(value, int):
                            filters.append(self._model.parameters[column].astext.cast(Integer) == value)
                        elif isinstance(value, str):
                            filters.append(self._model.parameters[column].astext == value)

                if starttime is not None:
                    filters.append(getattr(self._model, 'created_date') >= starttime)
                if endtime is not None:
                    filters.append(getattr(self._model, 'created_date') <= endtime)
                filter_query = session.query(self._model).filter(*filters)
                if self._model._str() == 'state_transition_log':
                    filter_query = filter_query.order_by(self._model.created_timestamp.desc())
                elif self._model._str() == 'transaction_log_audit':
                    filter_query = filter_query.order_by(self._model.timestamp.desc())
                elif self._model._str() == 'states':
                    filter_query = filter_query
                elif self._model._str() == 'automation_request':
                    filter_query = filter_query.order_by(self._model.created_date.desc())
                elif self._model._str() == 'queues':
                    filter_query = filter_query
                elif self._model._str() == 'resource_adapter_mapping':
                    filter_query = filter_query
                else:
                    filter_query = filter_query.order_by(self._model.created_date.desc())
                offset = (page - 1) * per_page
                if offset >= total:
                    return []
                execution = filter_query.offset(offset).limit(per_page).all()
                return execution
            except Exception as excp:
                raise excp

    def delete(self, iden_filters):
        with self.session_factory() as session:
            filters = [getattr(self._model, column) == value for column, value in iden_filters.items()]
            try:
                filter_query = session.query(self._model).filter(*filters)
                applications = filter_query.all()
                for application in applications:
                    session.delete(application)
                    session.commit()
                return applications
            except Exception as excp:
                raise excp

    def get_identifier(self, iden_filters):
        with self.session_factory() as session:
            filters = [getattr(self._model, column) == value for column, value in iden_filters.items()]
            try:
                if self._model._str() != 'state_transition_log':
                    return {}
                filter_query = session.query(self._model.plan_id, self._model.identifier,
                                             func.max(self._model.created_timestamp)).filter(*filters).group_by(
                    self._model.plan_id, self._model.identifier)
                rows = filter_query.all()
                return rows
            except sqexcp.NoResultFound as excp:
                raise Exception(
                    f'No record for table[{self._model._str()}] with applied filter[{iden_filters}]were found!')
            except AttributeError as excp:
                raise Exception(
                    f'Table[{self._model._str()}] has no column[{excp.__str__().split("attribute ", 1)[1]}]')
            except Exception as excp:
                raise excp

    def references_search(self, iden_filters, per_page, page):
        with self.session_factory() as session:
            try:
                print(self._model._str())
                if self._model._str() != 'automation_request':
                    return [], 0
                filters = []
                # filters = [self._model.references[column].astext.cast(Integer) == value  for column, value in iden_filters.items()]
                for column, value in iden_filters.items():
                    try:
                        if isinstance(value, int):
                            filters.append(self._model.references[column].astext.cast(Integer) == value)
                        elif isinstance(value, str):
                            filters.append(self._model.references[column].astext == value)
                    except Exception as excp:
                        pass
                filter_query = session.query(self._model).filter(*filters)
                filter_query = filter_query.order_by(self._model.created_date.desc())
                values = filter_query.all()
                total = len(values)
                offset = (page - 1) * per_page
                if offset >= total:
                    return [], total
                execution = filter_query.offset(offset).limit(per_page).all()
                return execution, total
            except Exception as excp:
                raise excp
