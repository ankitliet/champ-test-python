import os
import datetime
import logging
from cryptography.fernet import Fernet
import pytz
from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
import yaml
from fastapi_versioning import version
from dependency_injector.wiring import inject, Provide
from pydantic import ValidationError
import urllib.request
from util.core.app.config_audit import insert_config_audit
from core.app.schemas import *
from core.core.container import Container
from core.app.services import *
from sqlalchemy import create_engine, orm
from sqlalchemy import exc as sqexcp
from copy import deepcopy
import copy
from util.core.app.cipher_keys import AESCipher
from util.core.app.constants import TASK_STATUS
from util.core.app.models import AutomationPlan, AutomationTask, AutomationCode
from util.core.app.validate_license import validate_license
from core.app.services import CommonService
from typing import Optional

logger = logging.getLogger(__name__)

subapi = APIRouter(prefix='/dashUI', tags=['Data handling for User dashboard'])

with open(os.path.join(os.environ['BASEDIR'], 'core',
                       'core', 'settings', f'{os.environ["EXECFILE"]}.yml'), 'r') as file:
    documents = yaml.full_load(file)
_key = bytes(documents['password-encryption']['key'], 'utf-8')


def decrypt_password(decrypt_text):
    """
    function to decrypting passwords
    """
    cipher_suite = Fernet(_key)
    _pass = bytes(decrypt_text, 'utf-8')
    decode_text = cipher_suite.decrypt(_pass)
    return decode_text.decode('utf-8')


def encrypt_text(decrypt_text, encryption_key, encryption_iv):
    """
    function to encrypting passwords
    """
    _cipher = AESCipher(encryption_key, encryption_iv)
    encrypt_text = _cipher.encrypt(decrypt_text)
    return encrypt_text.decode('utf-8')
    # return decrypt_text


def convert_to_secure(_dict, encryption_key, encryption_iv):
    """
    function ------
    """
    _tmp = deepcopy(_dict)
    for key, value in _dict.items():
        key_name = "__e__" + key
        if isinstance(value, dict):
            convert_to_secure(value, encryption_key, encryption_iv)
        elif isinstance(value, str):
            _tmp.pop(key)
            _tmp[key_name] = encrypt_text(value, encryption_key, encryption_iv)
    return _tmp


def decrypt(encryped):
    """
    function ------
    """
    key = _key.decode('utf-8')
    encrypted = encryped.split('*')
    encrypted = [int(x) for x in encrypted]
    msg = []
    for i, c in enumerate(encrypted):
        key_c = ord(key[i % len(key)])  # ord  = character to unicode
        enc_c = c
        msg.append(chr((enc_c - key_c) % 127))  # chr = unicode to string
    return ''.join(msg)


def insert_config_audit_log(config_name, value, Operation, created_by, modified_by):
    """
    function to create config audit payload log
    """
    payload = {
        "config_name": config_name,
        "config_value": value,
        "operation_name": Operation,
        "created_by": created_by,
        "modified_by": modified_by
    }
    insert_config_audit(payload)


def update_op(iden_filters, model, session, **kwargs):
    """
    function to update op
    """
    if iden_filters:
        try:
            filters = [getattr(model, column) == value for column, value in iden_filters.items()]
            filter_query = session.query(model).filter(*filters)
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
    row = model(**kwargs)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def search_op(iden_filters, model, session):
    """
        function to update op
    """
    filters = [getattr(model, column) == value for column, value in iden_filters.items()]
    filter_query = session.query(model).filter(*filters)
    rows = filter_query.all()
    return rows


@subapi.post("/search")
@version(1, 0)
@inject
@validate_license
def search(
        body: SearchSchema,
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        state_trans_service: CommonService = Depends(Provide[Container.state_trans_service]),
        page: Optional[int] = 1,
        per_page: Optional[int] = 5
):
    """
            function to run search
    """
    try:
        filters = body.dict(exclude_unset=True)
        service = auto_task_service
        data = []
        filt = deepcopy(filters)
        # print(filt)
        total = service.fetch_all(filters)
        total = len(total)
        data1 = service.paginate_fetch(filt, page, per_page, total)
        # print([t.parameters for t in data1])
        identifiers = state_trans_service.get_identifier({})
        data_frame = pd.DataFrame(identifiers, columns=['task_id', 'identifier', 'timestamp'])
        data_frame = data_frame.sort_values('timestamp')
        data_frame = data_frame.drop_duplicates(subset="task_id", keep='first')
        data_frame = data_frame.set_index('task_id')
        for _data in data1:
            try:
                setattr(_data, 'blueprint_name', _data.parameters['blueprint_name'])
                setattr(_data, 'cust_sub_id', _data.parameters['cust_sub_id'])
                d1 = {_col: getattr(_data, _col) for _col in _data.__table__.columns.keys()}
                old_timezone = pytz.timezone('Etc/UTC')
                new_timezone = pytz.timezone('Asia/Kolkata')
                localized_created_time = old_timezone.localize(d1['created_date'])
                new_timezone_created_time = localized_created_time.astimezone(new_timezone)
                d1['created_date'] = new_timezone_created_time.strftime("%d-%m-%Y %H:%M:%S")
                localized_modified_time = old_timezone.localize(d1['modified_date'])
                new_timezone_modified_time = localized_modified_time.astimezone(new_timezone)
                d1['modified_date'] = new_timezone_modified_time.strftime("%d-%m-%Y %H:%M:%S")

                try:
                    if d1['status'] == 'IN_QUEUE':
                        d1['identifier'] = 'NA'
                    else:
                        d1['identifier'] = data_frame.loc[d1['task_id']].identifier
                except:
                    pass
                data.append(d1)

            except Exception as excp:
                pass

        resp = {'data': data, 'total': total}
        response = JSONResponse(content=jsonable_encoder(resp))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/details")
@version(1, 0)
@inject
@validate_license
def get_details(
        task_id: Optional[str] = 'All',
        name: Optional[str] = 'task',
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        auto_plan_service: CommonService = Depends(Provide[Container.auto_plan_service]),
        auto_code_service: CommonService = Depends(Provide[Container.auto_code_service]),
        audit_log_service: CommonService = Depends(Provide[Container.audit_log_service]),
        state_trans_service: CommonService = Depends(Provide[Container.state_trans_service]),
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service])
):
    """
            function to fetch details
    """
    try:
        services = {'task': auto_action_service,
                    'transition': state_trans_service,
                    'code': auto_code_service,
                    'plan': auto_plan_service,
                    'audit_log': audit_log_service,
                    'request': auto_task_service}
        filters = {}

        if task_id != 'All':
            request = auto_task_service.fetch({'task_id': task_id})
            action = auto_action_service.fetch(
                {'task_name': request.task_name,
                 'cloud_provider': request.parameters['cloud_provider']})
            if name == 'code' or name == 'plan':
                filters['task_id'] = action.id
            elif name == 'task':
                filters['task_name'] = request.task_name
            elif name == 'transition':
                filters['plan_id'] = task_id
            else:
                filters['task_id'] = task_id
        if name == 'request':
            service = services[name]
            data = []
            data1 = service.fetch_all(filters)
            identifiers = state_trans_service.get_identifier({})
            data_frame = pd.DataFrame(identifiers, columns=['task_id', 'identifier', 'timestamp'])
            data_frame = data_frame.sort_values('timestamp')
            data_frame = data_frame.drop_duplicates(subset="task_id", keep='first')
            data_frame = data_frame.set_index('task_id')
            for _data in data1:
                try:
                    setattr(_data, 'blueprint_name', _data.parameters['blueprint_name'])
                    setattr(_data, 'cust_sub_id', _data.parameters['cust_sub_id'])
                    d1 = {_col: getattr(_data, _col) for _col in _data.__table__.columns.keys()}
                    old_timezone = pytz.timezone('Etc/UTC')
                    new_timezone = pytz.timezone('Asia/Kolkata')
                    localized_created_time = old_timezone.localize(d1['created_date'])
                    new_timezone_created_time = localized_created_time.astimezone(new_timezone)
                    d1['created_date'] = new_timezone_created_time.strftime("%d-%m-%Y %H:%M:%S")
                    localized_modified_time = old_timezone.localize(d1['modified_date'])
                    new_timezone_modified_time = localized_modified_time.astimezone(new_timezone)
                    d1['modified_date'] = new_timezone_modified_time.strftime("%d-%m-%Y %H:%M:%S")

                    try:
                        if d1['status'] == 'IN_QUEUE':
                            d1['identifier'] = 'NA'
                        else:
                            d1['identifier'] = data_frame.loc[d1['task_id']].identifier
                    except:
                        pass
                    data.append(d1)

                except Exception as excp:
                    pass


        else:
            service = services[name]
            data = service.fetch_all(filters)
        response = JSONResponse(content=jsonable_encoder(data))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/all_details")
@version(1, 0)
@inject
@validate_license
def get_all_details(
        name: Optional[str] = 'task',
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5,
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        auto_plan_service: CommonService = Depends(Provide[Container.auto_plan_service]),
        auto_code_service: CommonService = Depends(Provide[Container.auto_code_service]),
        audit_log_service: CommonService = Depends(Provide[Container.audit_log_service]),
        state_trans_service: CommonService = Depends(Provide[Container.state_trans_service]),
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service])
):
    """
            function to fetch details of all data sets
        """
    try:
        services = {'task': auto_action_service,
                    'transition': state_trans_service,
                    'code': auto_code_service,
                    'plan': auto_plan_service,
                    'audit_log': audit_log_service,
                    'request': auto_task_service}
        filters = {}
        service = services[name]
        resp = {}
        values = service.fetch_all({})
        resp['total'] = len(values)
        data = service.paginate_fetch(iden_filters=filters,
                                      per_page=per_page,
                                      page=page_no,
                                      total=resp['total'])
        data1 = []
        if name == 'request':
            identifiers = state_trans_service.get_identifier({})
            data_frame = pd.DataFrame(identifiers, columns=['task_id', 'identifier', 'timestamp'])
            data_frame = data_frame.sort_values('timestamp')
            data_frame = data_frame.drop_duplicates(subset="task_id", keep='first')
            data_frame = data_frame.set_index('task_id')
            print(data_frame)

            for d in data:
                d1 = {_col: getattr(d, _col) for _col in d.__table__.columns.keys()}
                old_timezone = pytz.timezone('Etc/UTC')
                new_timezone = pytz.timezone('Asia/Kolkata')
                localized_created_time = old_timezone.localize(d1['created_date'])
                new_timezone_created_time = localized_created_time.astimezone(new_timezone)
                d1['created_date'] = new_timezone_created_time.strftime("%d-%m-%Y %H:%M:%S")
                localized_modified_time = old_timezone.localize(d1['modified_date'])
                new_timezone_modified_time = localized_modified_time.astimezone(new_timezone)
                d1['modified_date'] = new_timezone_modified_time.strftime("%d-%m-%Y %H:%M:%S")

                try:
                    if d1['status'] == 'IN_QUEUE':
                        d1['identifier'] = 'NA'
                    else:
                        d1['identifier'] = data_frame.loc[d1['task_id']].identifier
                except:
                    pass
                data1.append(d1)
        resp['data'] = data1
        response = JSONResponse(content=jsonable_encoder(resp))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/metadata")
@version(1, 0)
@inject
@validate_license
def get_metadata(
        task_id: Optional[str] = 'All',
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service])

):
    """
            function to get metadata
        """
    try:
        filters = {}
        if task_id != 'All':
            filters['task_id'] = task_id
        data = auto_task_service.fetch_all(filters)
        data_new = []
        for x in data:
            row = x.__dict__
            for k, v in row['parameters'].items():
                row[k] = v
            del row['parameters']
            data_new.append(row)
        response = JSONResponse(content=jsonable_encoder(data_new))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/states")
@version(1, 0)
@inject
@validate_license
def get_states(
        task_id: str,
        state_trans_service: CommonService = Depends(Provide[Container.state_trans_service]),
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        auto_plan_service: CommonService = Depends(Provide[Container.auto_plan_service]),
        auto_code_service: CommonService = Depends(Provide[Container.auto_code_service]),
        audit_log_service: CommonService = Depends(Provide[Container.audit_log_service]),
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service])
):
    """
            function to get states
        """
    try:
        filters = {}
        request = auto_task_service.fetch({'task_id': task_id})

        cloud_provider = request.parameters['cloud_provider']
        action = auto_action_service.fetch(
            {'task_name': request.task_name, 'cloud_provider': cloud_provider})
        filters['id'] = action.plan_id
        plan = auto_plan_service.fetch(filters)

        state_logs = state_trans_service.fetch_all({'plan_id': task_id})

        states = {}
        plan = plan.execution_plan

        logger.debug("Main plan is:%s" % plan)
        external_plans = None
        if 'external_plans' in plan.get('StateTransition'):
            external_plans = plan.get('StateTransition').pop('external_plans')
        if external_plans:
            for i in range(len(external_plans)):
                each_external_plan = external_plans[i]
                task_type = auto_action_service.fetch(
                    {'task_name': each_external_plan, 'cloud_provider': cloud_provider})
                sub_plan = auto_plan_service.fetch({'id': task_type.plan_id,
                                                    'cloud_provider': cloud_provider})
                sub_plan = sub_plan.execution_plan.get('StateTransition').get(each_external_plan)
                if not sub_plan:
                    raise Exception("No valid plan exist")
                if len(external_plans) > i + 1:
                    sub_plan["success"] = external_plans[i + 1]
                else:
                    sub_plan["success"] = "EndExecution"
                sub_plan["failure"] = "EndExecution"
                logger.debug("Sub Plan is:%s" % sub_plan)
                plan["StateTransition"][each_external_plan] = sub_plan
        logger.debug("Updated Main plan is:%s" % plan)

        parallel_tasks = []

        for k, v in plan['StateTransition'].items():
            states[k] = v
            states[k]['status'] = TASK_STATUS.NOT_INITIATED
            if 'parallel_tasks' in states[k]:
                parallel_tasks.append(k)
                for k1, v1 in states[k]['parallel_tasks'].items():
                    states[k]['parallel_tasks'][k1]['status'] = TASK_STATUS.NOT_INITIATED
        print(states)
        current_ptask = None

        # for x in state_logs:
        # print(x.current_state)

        for x in state_logs:
            # print(x.current_state)
            if x.current_state in parallel_tasks:
                current_ptask = x.current_state
            if x.current_state in states:
                if states[x.current_state]['status'] == TASK_STATUS.NOT_INITIATED:
                    states[x.current_state]['status'] = x.current_status
                    timestp = x.created_timestamp
                    old_timezone = pytz.timezone('Etc/UTC')
                    new_timezone = pytz.timezone('Asia/Kolkata')
                    localized_time = old_timezone.localize(timestp)
                    new_timezone_time = localized_time.astimezone(new_timezone)
                    states[x.current_state]['timestamp'] = new_timezone_time.strftime("%d-%m-%Y %H:%M:%S")
                    states[x.current_state]['message'] = x.kv_log

            elif current_ptask is not None:
                # print(current_ptask)
                for k, v in states[current_ptask]['parallel_tasks'].items():
                    if k == x.current_state:
                        if v['status'] == TASK_STATUS.NOT_INITIATED:
                            states[current_ptask]['parallel_tasks'][k]['status'] = x.current_status
                            timestp = x.created_timestamp
                            old_timezone = pytz.timezone('Etc/UTC')
                            new_timezone = pytz.timezone('Asia/Kolkata')
                            localized_time = old_timezone.localize(timestp)
                            new_timezone_time = localized_time.astimezone(new_timezone)
                            states[current_ptask]['parallel_tasks'][k]['timestamp'] = new_timezone_time.strftime(
                                "%d-%m-%Y %H:%M:%S")
                            states[current_ptask]['parallel_tasks'][k]['message'] = x.kv_log

        response = JSONResponse(content=jsonable_encoder(states))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/response")
@version(1, 0)
@inject
@validate_license
def get_response(
        task_id: str,
        states_service: CommonService = Depends(Provide[Container.states_service])
):
    """
            function to get response
    """
    try:
        states = states_service.fetch_like({'task_id': task_id})
        data = {}
        for x in states:
            data[x.name[len(task_id):]] = json.loads(x.data)

        response = JSONResponse(content=jsonable_encoder(data))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/workbench")
@version(1, 0)
@inject
@validate_license
def put_wb(
        wb: Catalouge,
        workbench_service: CommonService = Depends(Provide[Container.workbench_service])
):
    """
            function to edit or insert workbench
        """
    try:
        wb = wb.dict(exclude_unset=True)
        wb = workbench_service.create_or_update({'task_name': wb['task_name'], 'cloud_provider': wb['cloud_provider']},
                                                **wb)
        wb = {_col: getattr(wb, _col) for _col in wb.__table__.columns.keys()}
        response = JSONResponse(content=jsonable_encoder(wb))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/workbench")
@version(1, 0)
@inject
@validate_license
def get_wb(
        workbench_service: CommonService = Depends(Provide[Container.workbench_service]),
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service]),
        task_name: Optional[str] = None,
        cloud_provider: Optional[str] = None
):
    """
            function to get all workbench details
    """
    try:
        actions = {}
        if task_name is None or cloud_provider is None:
            tasks = auto_action_service.fetch_all({})
            for task in tasks:
                cp = task.cloud_provider
                name = task.task_name
                if cp in actions:
                    actions[cp].append(name)
                else:
                    actions[cp] = [name]
        else:
            actions = workbench_service.fetch_all({'task_name': task_name, 'cloud_provider': cloud_provider})
            if len(actions) > 0:
                actions = actions[0]
        response = JSONResponse(content=jsonable_encoder(actions))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/credentials")
@version(1, 0)
@inject
@validate_license
def put_credentials(
        cred: CredentialSchema,
        cred_service: CommonService = Depends(Provide[Container.cred_service])
):
    """
            function to update or insert credentials
    """
    try:
        cred = cred.dict(exclude_unset=True)
        modified_by = ''
        if "modified_by" in cred:
            modified_by = cred['modified_by']
            del cred['modified_by']
        if cred['password'] is not None:
            # encoded_text = base64.b64encode(bytes(cred['password'], 'utf-8'))
            cipher_suite = Fernet(_key)
            encoded_text = cipher_suite.encrypt(bytes(cred['password'], 'utf-8'))
            cred['password'] = encoded_text.decode('utf-8')
        cred_id = -1
        is_upd = False
        config_value = {}
        if 'id' in cred:
            cred_id = cred['id']
            is_upd = True
            config_value = cred_service.fetch({'id': cred_id})
            config_value = {_col: getattr(config_value, _col) for _col in config_value.__table__.columns.keys()}
        cred = cred_service.create_or_update({'id': cred_id}, **cred)
        cred = {_col: getattr(cred, _col) for _col in cred.__table__.columns.keys()}
        if is_upd:
            insert_config_audit_log('Credentials', config_value, 'UPDATE', modified_by, modified_by)
        response = JSONResponse(content=jsonable_encoder(cred))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/credentials")
@version(1, 0)
@inject
@validate_license
def delete_credentials(
        cred_id: int,
        modified_by: str,
        cred_service: CommonService = Depends(Provide[Container.cred_service])

):
    """
            function to delete credentials
    """
    try:
        creds = cred_service.delete({'id': cred_id})
        if len(creds) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp = {_col: getattr(creds[0], _col) for _col in creds[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:  # pylint: disable=bare-except
            pass
        insert_config_audit_log('Credentials', resp, 'DELETE', modified_by, modified_by)
        creds.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(creds))


    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/credentials")
@version(1, 0)
@inject
@validate_license
def get_credentials(
        cred_id: Optional[str] = 'All',
        cred_service: CommonService = Depends(Provide[Container.cred_service])
):
    """
            function to get credentials
    """
    try:
        creds = cred_service.fetch_all({})
        cred = []
        for c in creds:
            x = {_col: getattr(c, _col) for _col in c.__table__.columns.keys()}
            if 'password' in x:
                x['password'] = decrypt_password(x['password'])
                cred.append(x)
        if cred_id != 'All':
            cred = cred_service.fetch({'id': int(cred_id)})
            cred = {_col: getattr(cred, _col) for _col in cred.__table__.columns.keys()}
            if 'password' in cred:
                cred['password'] = decrypt_password(cred['password'])

        response = JSONResponse(content=jsonable_encoder(cred))


    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/code")
@version(1, 0)
@inject
@validate_license
def put_code(
        code: CodeSchema,
        auto_code_service: CommonService = Depends(Provide[Container.auto_code_service])
):
    """
            function to update or insert code
        """
    try:
        code = code.dict(exclude_unset=True)
        code_name = 'dummy_name'
        cloud_provider = code['cloud_provider']
        is_upd = True
        code1 = {}
        if 'name' in code:
            code_name = code['name']
        try:
            code1 = auto_code_service.fetch({'name': code_name, 'cloud_provider': code['cloud_provider']})
            code1 = {_col: getattr(code1, _col) for _col in code1.__table__.columns.keys()}
        except:  # pylint: disable=bare-except
            is_upd = False
        code = auto_code_service.create_or_update({'name': code_name, 'cloud_provider': cloud_provider}, **code)
        code = {_col: getattr(code, _col) for _col in code.__table__.columns.keys()}
        if is_upd:
            try:
                del code1['created_date']
                del code1['modified_date']
            except:  # pylint: disable=bare-except
                pass
            insert_config_audit_log('AutomationCode', code1, 'UPDATE', code['created_by'], code['modified_by'])
        response = JSONResponse(content=jsonable_encoder(code))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/code")
@version(1, 0)
@inject
@validate_license
def delete_code(
        code_id: int,
        modified_by: str,
        auto_code_service: CommonService = Depends(Provide[Container.auto_code_service])

):
    """
            function to delete code
    """
    try:
        codes = auto_code_service.delete({'id': code_id})
        if len(codes) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp = {_col: getattr(codes[0], _col) for _col in codes[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:  # pylint: disable=bare-except
            pass
        insert_config_audit_log('AutomationCode', resp, 'DELETE', modified_by, modified_by)
        codes.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(codes))


    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/code")
@version(1, 0)
@inject
@validate_license
def get_codes(
        task_id: Optional[str] = None,
        task_name: Optional[str] = None,
        cloud_provider: Optional[str] = None,
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        auto_code_service: CommonService = Depends(Provide[Container.auto_code_service])
):
    """
            function to get codes
        """
    try:
        code = []
        if task_id != 'All':
            if task_id is not None:
                request = auto_task_service.fetch_all({'task_id': task_id})
                if len(request) > 0:
                    code = auto_code_service.fetch_all(
                        {'name': request[0].task_name, 'cloud_provider': request[0].cloud_provider})
                    if len(code) > 0:
                        code = code[0]

            else:
                code = auto_code_service.fetch_all({'name': task_name, 'cloud_provider': cloud_provider})
                if len(code) > 0:
                    code = code[0]

        response = JSONResponse(content=jsonable_encoder(code))


    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/plan")
@version(1, 0)
@inject
@validate_license
def put_plan(
        plan: PlanSchema,
        auto_plan_service: CommonService = Depends(Provide[Container.auto_plan_service]),
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service])
):
    """
            function to update or insert plan
    """
    try:
        plan = plan.dict(exclude_unset=True)
        plan_id = -1
        if 'id' in plan:
            plan_id = plan['id']
        name = plan['name']
        schema = plan['input_schema']
        del plan['name']
        del plan['input_schema']
        plan = auto_plan_service.create_or_update({'id': plan_id}, **plan)
        plan = {_col: getattr(plan, _col) for _col in plan.__table__.columns.keys()}
        del plan['created_date']
        del plan['modified_date']
        del plan['execution_plan']
        task = auto_action_service.create_or_update({'name': name, 'cloud_provider': plan['cloud_provider']}, name=name,
                                                    task_name=name, plan_id=plan['id'],
                                                    cloud_provider=plan['cloud_provider'],
                                                    created_by=plan['created_by'], modified_by=plan['modified_by'])
        plan = auto_plan_service.fetch({'id': plan['id']})
        response = JSONResponse(content=jsonable_encoder(plan))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/update")
@version(1, 0)
@inject
@validate_license
def update(
        name: str,
        obj: PlanSchema,
        auto_plan_service: CommonService = Depends(Provide[Container.auto_plan_service]),
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service])
):
    """
            function to update
        """
    try:
        obj = obj.dict(exclude_unset=True)
        response = {}
        if name == 'plan':
            resp = {}
            try:
                plan_old = auto_plan_service.fetch({'id': obj['id']})
                resp = {_col: getattr(plan_old, _col) for _col in plan_old.__table__.columns.keys()}
            except:  # pylint: disable=bare-except
                pass
            plan = auto_plan_service.create_or_update({'id': obj['id']}, **obj)
            plan = {_col: getattr(plan, _col) for _col in plan.__table__.columns.keys()}
            response = plan
            try:
                del resp['created_date']
                del resp['modified_date']
            except:  # pylint: disable=bare-except
                pass
            insert_config_audit_log('AutomationPlan', resp, 'UPDATE', plan['created_by'], plan['modified_by'])

        elif name == 'task':
            task = auto_action_service.create_or_update({'name': obj['name'], 'cloud_provider': obj['cloud_provider']},
                                                        **obj)
            resp = {_col: getattr(task, _col) for _col in task.__table__.columns.keys()}
            response = task

        response = JSONResponse(content=jsonable_encoder(response))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/plan")
@version(1, 0)
@inject
@validate_license
def delete_plan(
        plan_id: int,
        delete_code: bool,
        modified_by: str,
        auto_plan_service: CommonService = Depends(Provide[Container.auto_plan_service]),
        auto_code_service: CommonService = Depends(Provide[Container.auto_code_service]),
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service])

):
    """
            function to delete plan
    """
    try:
        task = auto_action_service.fetch({'plan_id': plan_id})
        plans = auto_plan_service.delete({'id': plan_id})
        if len(plans) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp = {_col: getattr(plans[0], _col) for _col in plans[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:  # pylint: disable=bare-except
            pass
        insert_config_audit_log('AutomationPlan', resp, 'DELETE', modified_by, modified_by)
        tasks = auto_action_service.delete({'id': task.id})
        if delete_code:
            try:
                code = auto_code_service.delete({'name': task.name, 'cloud_provider': task.cloud_provider})
                if len(code) == 0:
                    response = JSONResponse(content=jsonable_encoder({}))
                    return response
                resp = {_col: getattr(code[0], _col) for _col in code[0].__table__.columns.keys()}
                try:
                    del resp['created_date']
                    del resp['modified_date']
                except:  # pylint: disable=bare-except
                    pass
                insert_config_audit_log('AutomationCode', resp, 'DELETE', modified_by, modified_by)
                plans.append({'message': 'Code Successfully deleted'})
            except Exception as ex:
                plans.append({'message': str(ex)})
        plans.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(plans))


    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/task")
@version(1, 0)
@inject
@validate_license
def delete_task(
        name: str,
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service])
):
    """
            function to delete task
        """
    try:
        tasks = auto_action_service.delete({'name': name})
        tasks.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(tasks))


    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/plan")
@version(1, 0)
@inject
@validate_license
def get_plan(
        task_id: Optional[str] = None,
        task_name: Optional[str] = None,
        cloud_provider: Optional[str] = None,
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        auto_plan_service: CommonService = Depends(Provide[Container.auto_plan_service]),
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service])
):
    """
            function to get all plan details
        """
    try:
        plan = []
        if task_id != 'All':
            if task_id is not None:
                request = auto_task_service.fetch_all({'task_id': task_id})
                if len(request) > 0:
                    task = auto_action_service.fetch_all(
                        {'name': request[0].task_name, 'cloud_provider': request[0].cloud_provider})
                    if len(task) > 0:
                        plan = auto_plan_service.fetch_all({'id': int(task[0].plan_id)})
                        if len(plan) > 0:
                            plan = plan[0]
                            plan = {_col: getattr(plan, _col) for _col in plan.__table__.columns.keys()}
                            if 'task' in plan:
                                del plan['task']


            else:
                task = auto_action_service.fetch_all({'name': task_name, 'cloud_provider': cloud_provider})
                if len(task) > 0:
                    plan = auto_plan_service.fetch_all({'id': int(task[0].plan_id)})
                    if len(plan) > 0:
                        plan = plan[0]
                        plan = {_col: getattr(plan, _col) for _col in plan.__table__.columns.keys()}
                        if 'task' in plan:
                            del plan['task']

        response = JSONResponse(content=jsonable_encoder(plan))


    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/application")
@version(1, 0)
@inject
@validate_license
def put_app(
        app: ApplicationSchema,
        application_service: CommonService = Depends(Provide[Container.application_service])
):
    """
            function to update op
    """
    try:
        app = app.dict(exclude_unset=True)
        app_id = -1
        is_upd = False
        app_old = {}
        if 'id' in app:
            app_id = app['id']
            is_upd = True
            try:
                app_old = application_service.fetch({'id': app_id})
                app_old = {_col: getattr(app_old, _col) for _col in app_old.__table__.columns.keys()}
            except:  # pylint: disable=bare-except
                pass
        app = application_service.create_or_update({'id': app_id}, **app)
        app = {_col: getattr(app, _col) for _col in app.__table__.columns.keys()}
        if is_upd:
            try:
                del app_old['created_date']
                del app_old['modified_date']
            except:  # pylint: disable=bare-except
                pass
            insert_config_audit_log('Application', app_old, 'UPDATE', app['created_by'], app['modified_by'])
        response = JSONResponse(content=jsonable_encoder(app))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/application")
@version(1, 0)
@inject
@validate_license
def delete_app(
        id: int,
        modified_by: str,
        application_service: CommonService = Depends(Provide[Container.application_service])

):
    """
            function to delete application
    """
    try:
        apps = application_service.delete({'id': id})
        if len(apps) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp = {_col: getattr(apps[0], _col) for _col in apps[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:  # pylint: disable=bare-except
            pass
        insert_config_audit_log('Application', resp, 'DELETE', modified_by, modified_by)
        apps.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(apps))


    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/application")
@version(1, 0)
@inject
@validate_license
def get_app(
        source: Optional[str] = 'All',
        application_service: CommonService = Depends(Provide[Container.application_service]),
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5
):
    """
            function to get application
    """
    try:

        if source != 'All':
            app = application_service.fetch({'source': source})
        else:
            resp = {}
            apps = application_service.fetch_all({})
            total = len(apps)
            resp['data'] = application_service.paginate_fetch({}, per_page=per_page, page=page_no, total=total)
            resp['total'] = total

        response = JSONResponse(content=jsonable_encoder(resp))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/dropdowns")
@version(1, 0)
@inject
@validate_license
def get_dropdowns(
        name: Optional[str] = 'task_id',
        cloud_provider: Optional[str] = 'All',
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service])
):
    """
            function to get dropdowns
    """
    try:
        filters = {}
        if cloud_provider != 'All':
            filters['cloud_provider'] = cloud_provider
        requests = auto_task_service.fetch_all(filters)
        data = {'task_id': [], 'task_name': [], 'cloud_provider': []}
        for request in requests:
            data['task_id'].append(request.task_id)

        tasks = auto_action_service.fetch_all(filters)
        for task in tasks:
            data['task_name'].append(task.task_name)
            data['cloud_provider'].append(task.cloud_provider)

        resp = list(set(data[name]))
        resp.sort()
        response = JSONResponse(content=jsonable_encoder(resp))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/agent")
@version(1, 0)
@inject
@validate_license
def put_agent(
        agent: AgentSchema,
        agent_service: CommonService = Depends(Provide[Container.agent_service])
):
    """
            function to update or insert agent
        """
    try:
        agent = agent.dict(exclude_unset=True)
        agent_id = -1
        if 'id' in agent:
            agent_id = agent['id']
        agent = agent_service.create_or_update({'id': agent_id}, **agent)
        agent = {_col: getattr(agent, _col) for _col in agent.__table__.columns.keys()}
        response = JSONResponse(content=jsonable_encoder(agent))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/agent")
@version(1, 0)
@inject
@validate_license
def delete_agent(
        id: int,
        agent_service: CommonService = Depends(Provide[Container.agent_service])
):
    """
            function to delete agent
        """
    try:
        agents = agent_service.delete({'id': id})
        agents.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(agents))


    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/agent")
@version(1, 0)
@inject
@validate_license
def get_agent(
        node_name: Optional[str] = 'All',
        agent_service: CommonService = Depends(Provide[Container.agent_service]),
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5
):
    """
            function to get all agent info
        """
    try:

        if node_name != 'All':
            agent = agent_service.fetch({'node_name': node_name})
            url = agent.url
            agent = {_col: getattr(agent, _col) for _col in agent.__table__.columns.keys()}
            agent['status'] = {}
            try:
                obj = urllib.request.urlopen(url)
                status_code = obj.getcode()
                agent['status']['status_code'] = status_code
                response = obj.read().decode("utf8", 'ignore')
                agent['status']['response'] = 'url is working alright'

            except urllib.error.HTTPError as e:
                body = e.read().decode()
                agent['status']['response'] = body

            except Exception as e:
                agent['status']['response'] = str(e)

        else:
            agents = agent_service.fetch_all({})
            total = len(agents)
            agent = []
            agents = agent_service.paginate_fetch({}, per_page=per_page, page=page_no, total=total)
            for x in agents:
                url = x.url
                agt = {_col: getattr(x, _col) for _col in x.__table__.columns.keys()}
                agt['status'] = {}
                try:
                    obj = urllib.request.urlopen(url)
                    status_code = obj.getcode()
                    agt['status']['status_code'] = status_code
                    response = obj.read().decode("utf8", 'ignore')
                    agt['status']['response'] = 'url is working alright'

                except urllib.error.HTTPError as e:
                    body = e.read().decode()
                    agt['status']['response'] = body
                except Exception as e:
                    agt['status']['response'] = str(e)

                agent.append(agt)

            resp = {}
            resp['data'] = agent
            resp['total'] = total
        response = JSONResponse(content=jsonable_encoder(resp))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/dashboard")
@version(1, 0)
@inject
@validate_license
def get_request_dashboard(
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        starttime: Optional[str] = '1970-01-01 05:30:00',
        endtime: Optional[str] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
):
    """
            function to get dashboard information
        """
    '''Returns dashboard data'''
    try:
        old_timezone = pytz.timezone('Etc/UTC')
        new_timezone = pytz.timezone('Asia/Kolkata')
        localized_starttime = new_timezone.localize(datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S'))
        new_timezone_starttime = localized_starttime.astimezone(old_timezone)
        localized_endtime = new_timezone.localize(datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S'))
        new_timezone_endtime = localized_endtime.astimezone(old_timezone)
        starttime_utc = str(new_timezone_starttime.strftime('%Y-%m-%d %H:%M:%S'))
        endtime_utc = str(new_timezone_endtime.strftime('%Y-%m-%d %H:%M:%S'))
        response = auto_task_service.dashboard(starttime=starttime_utc, endtime=endtime_utc)
        json_compatible_execution_data = jsonable_encoder(response)
        response = JSONResponse(content=json_compatible_execution_data)
    except Exception as excp:
        logger.exception(excp)
        response = JSONResponse(content=dict(error=excp.__str__()))
    return response


@subapi.get("/processor_insights")
@version(1, 0)
@inject
@validate_license
def get_insights(
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        starttime: Optional[str] = '1970-01-01 05:30:00',
        endtime: Optional[str] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
):
    """
            function to get insights
        """
    '''Returns dashboard data'''
    try:
        old_timezone = pytz.timezone('Etc/UTC')
        new_timezone = pytz.timezone('Asia/Kolkata')
        localized_starttime = new_timezone.localize(datetime.strptime(starttime, '%Y-%m-%d %H:%M:%S'))
        new_timezone_starttime = localized_starttime.astimezone(old_timezone)
        localized_endtime = new_timezone.localize(datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S'))
        new_timezone_endtime = localized_endtime.astimezone(old_timezone)
        starttime_utc = str(new_timezone_starttime.strftime('%Y-%m-%d %H:%M:%S'))
        endtime_utc = str(new_timezone_endtime.strftime('%Y-%m-%d %H:%M:%S'))
        response = auto_task_service.processor_insights(starttime=starttime_utc, endtime=endtime_utc)
        json_compatible_execution_data = jsonable_encoder(response)
        response = JSONResponse(content=json_compatible_execution_data)
    except Exception as excp:
        logger.exception(excp)
        response = JSONResponse(content=dict(error=excp.__str__()))
    return response


@subapi.post("/authenticate")
@version(1, 0)
@inject
@validate_license
def validate_user(
        user: LoginUserSchema,
        request: Request,
        user_service: CommonService = Depends(Provide[Container.user_service])
):
    """
            function to authenticate user
        """
    '''Returns dashboard data'''
    response = {}
    try:
        username = str(user.username).lower()
        password = user.password

        user_detail = user_service.fetch({'user_name': username, 'is_active': True})
        user_detail = {_col: getattr(user_detail, _col) for _col in user_detail.__table__.columns.keys()}

        if str(user_detail['user_name']).lower() == username and \
                decrypt_password(user_detail['password']) == password:
            response["iss"] = request.url._url
            response['given_name'] = user_detail['first_name']
            response['family_name'] = user_detail['last_name']
            response['email'] = user_detail['email_address']
            response['name'] = "{} {}".format(user_detail['first_name'], user_detail['last_name'])
            response['email_verified'] = True
        else:
            response['email_verified'] = False
        json_compatible_execution_data = jsonable_encoder(response)
        response = JSONResponse(content=json_compatible_execution_data)
    except Exception as excp:
        logger.exception(excp)
        response['email_verified'] = False
        response['error'] = dict(msg=excp.__str__())
        response = JSONResponse(content=response)
    return response


@subapi.get("/config_audit")
@version(1, 0)
@inject
@validate_license
def get_config_audit(
        operation_name: Optional[str] = 'All',
        config_name: Optional[str] = 'All',
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5,
        audit_config_service: CommonService = Depends(Provide[Container.audit_config_service]),
):
    """
            function to get config audit details
    """
    try:
        resp = {}
        filters = {}
        if operation_name != 'All':
            filters['operation_name'] = operation_name
        if config_name != 'All':
            filters['config_name'] = config_name

        values = audit_config_service.fetch_all(filters)
        resp['total'] = len(values)
        data = audit_config_service.paginate_fetch(iden_filters=filters, per_page=per_page, page=page_no,
                                                   total=resp['total'])
        resp['data'] = data
        response = JSONResponse(content=jsonable_encoder(resp))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.post("/migrate_task")
@version(1, 0)
@inject
@validate_license
def migrate_task(
        body: dict,
        auto_plan_service: CommonService = Depends(Provide[Container.auto_plan_service]),
        auto_code_service: CommonService = Depends(Provide[Container.auto_code_service]),
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service])
):
    """
            function to migrate task
        """
    try:
        resp = []
        source = body.get('source')
        dest = None
        if 'destination' in body:
            dest = body.get('destination')
        created_by = body.get('created_by')
        branch_name = source.get('branch_name')
        ################Source Session#################################
        db_url = source.get('db_url')
        db_schema = source.get('schema')
        _engine = create_engine(
            db_url, pool_size=20, max_overflow=15, echo=False,
            pool_recycle=300, pool_pre_ping=True, pool_use_lifo=True,
            connect_args={'options': '-csearch_path={}'.format(db_schema)}
        )
        _session = orm.scoped_session(
            orm.sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=_engine,
            ),
        )
        #######################################################################
        ##########################Destination Session###########################
        _session_dest = None
        if dest is not None:
            db_url = dest.get('db_url')
            db_schema = dest.get('schema')
            _engine_dest = create_engine(
                db_url, pool_size=20, max_overflow=15, echo=False,
                pool_recycle=300, pool_pre_ping=True, pool_use_lifo=True,
                connect_args={'options': '-csearch_path={}'.format(db_schema)}
            )
            _session_dest = orm.scoped_session(
                orm.sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=_engine_dest,
                ),
            )

        ########################################################################
        filters = []
        filter_query = _session.query(AutomationTask).filter(*filters)
        tasks = filter_query.all()
        for task in tasks:
            t = {_col: getattr(task, _col) for _col in task.__table__.columns.keys()}
            if dest is None:
                ext_tasks = auto_action_service.fetch_all(
                    {'task_name': t['task_name'], 'cloud_provider': t['cloud_provider']})
            else:
                ext_tasks = search_op({'task_name': t['task_name'], 'cloud_provider': t['cloud_provider']},
                                      AutomationTask, _session_dest)
            if len(ext_tasks) == 0:
                filters = [getattr(AutomationPlan, 'id') == t['plan_id']]
                filter_query = _session.query(AutomationPlan).filter(*filters)
                plans = filter_query.all()
                try:
                    plan = plans[0]
                except Exception as ex:
                    raise Exception('No plan for {} exists in source'.format(t['task_name']))
                name = t['task_name']
                schema = {}
                plan = {_col: getattr(plan, _col) for _col in plan.__table__.columns.keys()}
                del plan['id']
                del plan['created_date']
                del plan['modified_date']
                plan['created_by'] = created_by
                plan['modified_by'] = created_by

                if dest is None:
                    plan = auto_plan_service.create_or_update({'id': -1}, **plan)
                else:
                    plan = update_op({'id': -1}, AutomationPlan, _session_dest, **plan)
                plan = {_col: getattr(plan, _col) for _col in plan.__table__.columns.keys()}
                del plan['created_date']
                del plan['modified_date']
                del plan['execution_plan']
                if dest is None:
                    task = auto_action_service.create_or_update(
                        {'name': name, 'cloud_provider': plan['cloud_provider']}, name=name, task_name=name,
                        plan_id=plan['id'], cloud_provider=plan['cloud_provider'], created_by=plan['created_by'],
                        modified_by=plan['modified_by'])
                else:
                    task = update_op({'name': name, 'cloud_provider': plan['cloud_provider']}, AutomationTask,
                                     _session_dest, name=name, task_name=name, plan_id=plan['id'],
                                     cloud_provider=plan['cloud_provider'], created_by=plan['created_by'],
                                     modified_by=plan['modified_by'])
                # plan = auto_plan_service.fetch({'id':plan['id']})
                resp.append('Plan for task {} added'.format(t['task_name']))
                filters = [getattr(AutomationCode, 'name') == t['task_name'],
                           getattr(AutomationCode, 'cloud_provider') == t['cloud_provider']]
                filter_query = _session.query(AutomationCode).filter(*filters)
                codes = filter_query.all()
                flag_code = True
                try:
                    code = codes[0]
                except Exception as ex:
                    flag_code = False
                    pass
                if flag_code:
                    code = {_col: getattr(code, _col) for _col in code.__table__.columns.keys()}
                    del code['id']
                    del code['created_date']
                    del code['modified_date']
                    code['created_by'] = created_by
                    code['modified_by'] = created_by
                    code['branch'] = branch_name
                    if dest is None:
                        code = auto_code_service.create_or_update({'id': -1}, **code)
                    else:
                        code = update_op({'id': -1}, AutomationCode, _session_dest, **code)
                    resp.append('Code for task {} added'.format(t['task_name']))

            else:
                filters = [getattr(AutomationPlan, 'id') == t['plan_id']]
                filter_query = _session.query(AutomationPlan).filter(*filters)
                plans = filter_query.all()
                try:
                    plan = plans[0]
                except Exception as ex:
                    raise Exception('No plan for {} exists in source'.format(t['task_name']))

                plan = {_col: getattr(plan, _col) for _col in plan.__table__.columns.keys()}
                del plan['id']
                del plan['created_date']
                del plan['modified_date']
                plan['created_by'] = created_by
                plan['modified_by'] = created_by
                plan_id = ext_tasks[0].plan_id
                if dest is None:
                    plan = auto_plan_service.create_or_update({'id': plan_id}, **plan)
                else:
                    plan = update_op({'id': plan_id}, AutomationPlan, _session_dest, **plan)
                resp.append('Plan for task {} updated'.format(t['task_name']))
                filters = [getattr(AutomationCode, 'name') == t['task_name'],
                           getattr(AutomationCode, 'cloud_provider') == t['cloud_provider']]
                filter_query = _session.query(AutomationCode).filter(*filters)
                codes = filter_query.all()
                flag_code = True
                try:
                    code = codes[0]
                except Exception as ex:
                    flag_code = False
                    pass
                if flag_code:
                    code = {_col: getattr(code, _col) for _col in code.__table__.columns.keys()}
                    del code['id']
                    del code['created_date']
                    del code['modified_date']
                    code['created_by'] = created_by
                    code['modified_by'] = created_by
                    code['branch'] = branch_name
                    if dest is None:
                        code = auto_code_service.create_or_update(
                            {'name': t['task_name'], 'cloud_provider': t['cloud_provider']}, **code)
                    else:
                        code = update_op({'name': t['task_name'], 'cloud_provider': t['cloud_provider']},
                                         AutomationCode, _session_dest, **code)
                    resp.append('Code for task {} updated'.format(t['task_name']))

        response = JSONResponse(content=jsonable_encoder(resp))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.post("/migrate_catalouge")
@version(1, 0)
@inject
@validate_license
def migrate_catalouge(
        body: dict,
        workbench_service: CommonService = Depends(Provide[Container.workbench_service])
):
    """
            function to migrate catalouge data
        """
    try:
        resp = []
        source = body.get('source')
        dest = None
        if 'destination' in body:
            dest = body.get('destination')
        created_by = body.get('created_by')
        ################Source Session#################################
        db_url = source.get('db_url')
        db_schema = source.get('schema')
        _engine = create_engine(
            db_url, pool_size=20, max_overflow=15, echo=False,
            pool_recycle=300, pool_pre_ping=True, pool_use_lifo=True,
            connect_args={'options': '-csearch_path={}'.format(db_schema)}
        )
        _session = orm.scoped_session(
            orm.sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=_engine,
            ),
        )
        #######################################################################
        ##########################Destination Session###########################
        _session_dest = None
        if dest is not None:
            db_url = dest.get('db_url')
            db_schema = dest.get('schema')
            _engine_dest = create_engine(
                db_url, pool_size=20, max_overflow=15, echo=False,
                pool_recycle=300, pool_pre_ping=True, pool_use_lifo=True,
                connect_args={'options': '-csearch_path={}'.format(db_schema)}
            )
            _session_dest = orm.scoped_session(
                orm.sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=_engine_dest,
                ),
            )

        ########################################################################
        filters = []
        filter_query = _session.query(WorkBench).filter(*filters)
        tasks = filter_query.all()
        for task in tasks:
            t = {_col: getattr(task, _col) for _col in task.__table__.columns.keys()}
            # ext_tasks = workbench_service.fetch_all({'task_name': t['task_name'],'cloud_provider': t['cloud_provider']})
            filters = [getattr(WorkBench, 'task_name') == t['task_name'],
                       getattr(WorkBench, 'cloud_provider') == t['cloud_provider']]
            filter_query = _session.query(WorkBench).filter(*filters)
            loads = filter_query.all()
            try:
                load = loads[0]
            except Exception as ex:
                raise Exception('No payload for {} exists in source'.format(t['task_name']))
            load = {_col: getattr(load, _col) for _col in load.__table__.columns.keys()}
            del load['id']
            del load['created_date']
            if dest is None:
                load = workbench_service.create_or_update(
                    {'task_name': t['task_name'], 'cloud_provider': t['cloud_provider']}, **load)
            else:
                load = update_op({'task_name': t['task_name'], 'cloud_provider': t['cloud_provider']}, WorkBench,
                                 _session_dest, **load)
            resp.append(
                'Payload for task {},cloud provider {} added/updated'.format(t['task_name'], t['cloud_provider']))
        response = JSONResponse(content=jsonable_encoder(resp))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.post("/migrate_config")
@version(1, 0)
@inject
@validate_license
def migrate_config(
        body: dict,
        config_types: str,
        api_config_service: CommonService = Depends(Provide[Container.api_config_service]),
        default_config_service: CommonService = Depends(Provide[Container.default_config_service]),
        dbconfig_service: CommonService = Depends(Provide[Container.dbconfig_service])

):
    """
            function to migrate configration data
        """
    try:
        resp = []
        source = body.get('source')
        dest = None
        if 'destination' in body:
            dest = body.get('destination')
        created_by = body.get('created_by')
        services = {'task': default_config_service, 'system': dbconfig_service, 'api': api_config_service}
        models = {'task': DefaultConfig, 'system': DBConfigModel, 'api': APIConfig}
        ################Source Session#################################
        db_url = source.get('db_url')
        db_schema = source.get('schema')
        _engine = create_engine(
            db_url, pool_size=20, max_overflow=15, echo=False,
            pool_recycle=300, pool_pre_ping=True, pool_use_lifo=True,
            connect_args={'options': '-csearch_path={}'.format(db_schema)}
        )
        _session = orm.scoped_session(
            orm.sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=_engine,
            ),
        )
        #######################################################################
        ##########################Destination Session###########################
        _session_dest = None
        if dest is not None:
            db_url = dest.get('db_url')
            db_schema = dest.get('schema')
            _engine_dest = create_engine(
                db_url, pool_size=20, max_overflow=15, echo=False,
                pool_recycle=300, pool_pre_ping=True, pool_use_lifo=True,
                connect_args={'options': '-csearch_path={}'.format(db_schema)}
            )
            _session_dest = orm.scoped_session(
                orm.sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=_engine_dest,
                ),
            )

        ########################################################################
        for name in config_types.split(','):
            filters = []
            service = services[name]
            model = models[name]
            filter_query = _session.query(model).filter(*filters)
            configs = filter_query.all()
            for config in configs:
                t = {_col: getattr(config, _col) for _col in config.__table__.columns.keys()}
                # ext_tasks = workbench_service.fetch_all({'task_name': t['task_name'],'cloud_provider': t['cloud_provider']})
                # filters = [getattr(WorkBench, 'task_name')==t['task_name'],getattr(WorkBench, 'cloud_provider')==t['cloud_provider']]
                # filter_query = _session.query(WorkBench).filter(*filters)
                # loads = filter_query.all()
                # try:
                #    load = loads[0]
                # except Exception as ex:
                #    raise Exception('No payload for {} exists in source'.format(t['task_name']))
                # load = {_col:getattr(load, _col) for _col in load.__table__.columns.keys()}
                del t['id']
                if 'created_date' in t:
                    del t['created_date']
                if 'created_by' in t:
                    t['created_by'] = created_by
                if dest is None:
                    if name == 'task':
                        load = service.create_or_update(
                            {'task_name': t['task_name'], 'cloud_provider': t['cloud_provider']}, **t)
                    elif name == 'api':
                        load = service.create_or_update(
                            {'task_name': t['task_name'], 'cloud_provider': t['cloud_provider'],
                             'application_name': t['application_name']}, **t)
                    elif name == 'system':
                        load = service.create_or_update({'key': t['key']}, **t)
                else:
                    if name == 'task':
                        load = update_op({'task_name': t['task_name'], 'cloud_provider': t['cloud_provider']}, model,
                                         _session_dest, **t)
                    elif name == 'api':
                        # print(t)
                        load = update_op({'task_name': t['task_name'], 'cloud_provider': t['cloud_provider'],
                                          'application_name': t['application_name']}, model, _session_dest, **t)
                    elif name == 'system':
                        load = update_op({'key': t['key']}, model, _session_dest, **t)
                if name == 'api':
                    resp.append('Config({}) for task {},cloud provider {},application_name {} added/updated'.format(
                        model._str(), t['task_name'], t['cloud_provider'], t['application_name']))
                elif name == 'task':
                    resp.append(
                        'Config({}) for task {},cloud provider {}  added/updated'.format(model._str(), t['task_name'],
                                                                                         t['cloud_provider']))
                elif name == 'system':
                    resp.append('Config({}) for key {} added/updated'.format(model._str(), t['key']))

        response = JSONResponse(content=jsonable_encoder(resp))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/queues")
@version(1, 0)
@inject
@validate_license
def get_queues(
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5,
        queues_service: CommonService = Depends(Provide[Container.queues_service]),
):
    """
            function to all get queues
        """
    try:
        resp = {}
        values = queues_service.fetch_all({})
        resp['total'] = len(values)
        data = queues_service.paginate_fetch({}, per_page=per_page, page=page_no, total=resp['total'])
        resp['data'] = data
        response = JSONResponse(content=jsonable_encoder(resp))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/queues")
@version(1, 0)
@inject
@validate_license
def add_queues(
        queue: QueuesSchema,
        queues_service: CommonService = Depends(Provide[Container.queues_service])
):
    '''Returns dashboard data'''
    try:
        resp = {}
        load = queues_service.create_or_update({'id': queue.__dict__.get('id', -1)}, **queue.__dict__)
        resp['message'] = 'Payload for queue ' + queue.queue_name + ' added/updated'
        resp['queue_name'] = queue.queue_name
        response = JSONResponse(content=jsonable_encoder(resp))
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/queues")
@version(1, 0)
@inject
@validate_license
def delete_queues(
        queue_id: int,
        queues_service: CommonService = Depends(Provide[Container.queues_service])
):
    '''Returns dashboard data'''
    try:
        resp = {}
        load = queues_service.delete({'id': queue_id})
        resp['message'] = 'queue ' + str(queue_id) + ' deleted'
        response = JSONResponse(content=jsonable_encoder(resp))
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/adapter")
@version(1, 0)
@inject
@validate_license
def get_adapter(
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5,
        resource_adapter_mapping_service: CommonService = Depends(Provide[Container.resource_adapter_mapping_service]),
):
    """
            function to get all adapters
        """
    try:
        resp = {}
        values = resource_adapter_mapping_service.fetch_all({})
        resp['total'] = len(values)
        data = resource_adapter_mapping_service.paginate_fetch({}, per_page=per_page, page=page_no, total=resp['total'])
        resp['data'] = data
        response = JSONResponse(content=jsonable_encoder(resp))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/queues_provider_mappings")
@version(1, 0)
@inject
# @validate_license
def get_queues(
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5,
        queues_service: CommonService = Depends(Provide[Container.queues_service]),
        resource_adapter_mapping_service: CommonService = Depends(Provide[Container.resource_adapter_mapping_service])
):
    """
            function to get queues
        """
    try:
        resp = {}
        values = queues_service.fetch_all({})
        resp['total'] = len(values)
        data = queues_service.paginate_fetch({}, per_page=per_page, page=page_no, total=resp['total'])
        for d in data:
            mapping = resource_adapter_mapping_service.fetch_all({'queue_id': d.id})
            mapping_name = []
            for m in mapping:
                mapping_name.append(m.cloud_provider)
            d.__dict__['mapping_names'] = mapping_name
        resp['data'] = data
        response = JSONResponse(content=jsonable_encoder(resp))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/queues_provider_mappings")
@version(1, 0)
@inject
@validate_license
def add_providers(
        resource_adapter_mapping: ResourceAdapterMappingSchema,
        resource_adapter_mapping_service: CommonService = Depends(Provide[Container.resource_adapter_mapping_service])
):
    '''Returns dashboard data'''
    try:
        resp = {}
        temp = copy.deepcopy(resource_adapter_mapping)
        if temp.__dict__.get('queue_id'):
            mapping = resource_adapter_mapping_service.fetch_all({'queue_id': temp.__dict__.get('queue_id', -1)})
            for m in mapping:
                # make_null = resource_adapter_mapping_service.create_or_update({'id': m.id}, **{'id': m.id, 'cloud_provider': m.cloud_provider, 'queue_id': None})
                make_null = resource_adapter_mapping_service.create_or_update({'id': m.id}, **m)
        for ram in temp.data:
            # load = resource_adapter_mapping_service.create_or_update({'id': ram.get('id',-1)},**{'id': ram.get('id',None), 'cloud_provider': ram.get('cloud_provider'), 'queue_id': temp.__dict__.get('queue_id',-1)})
            ram_id = ram.get('id', -1)
            if ram_id != -1:
                del ram['id']
            load = resource_adapter_mapping_service.create_or_update({'id': ram_id}, **ram)
            resp['message'] = 'Payload for resource adapter ' + ram.get('cloud_provider') + ' added/updated'
            resp['cloud_provider'] = ram.get('cloud_provider')
            if temp.queue_id:
                resp['queue_id'] = temp.queue_id
            response = JSONResponse(content=jsonable_encoder(resp))
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/queues_provider_mappings")
@version(1, 0)
@inject
@validate_license
def delete_queues(
        resource_adapter_mapping_id: int,
        resource_adapter_mapping_service: CommonService = Depends(Provide[Container.resource_adapter_mapping_service])
):
    '''Returns dashboard data'''
    try:
        resp = {}
        load = resource_adapter_mapping_service.delete({'id': resource_adapter_mapping_id})
        resp['message'] = 'resource_adapter_mapping_id ' + str(resource_adapter_mapping_id) + ' deleted'
        response = JSONResponse(content=jsonable_encoder(resp))
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/task_config")
@version(1, 0)
@inject
@validate_license
def get_default_config(
        task_name: str,
        cloud_provider: str,
        default_config_service: CommonService = Depends(Provide[Container.default_config_service])
):
    """
            function to get all default config
        """
    try:
        conf = default_config_service.fetch_all({'task_name': task_name, 'cloud_provider': cloud_provider})
        response = JSONResponse(content=jsonable_encoder(conf))
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/task_config")
@version(1, 0)
@inject
@validate_license
def upsert_default_config(
        task_name: str,
        cloud_provider: str,
        default_values: dict,
        default_config_service: CommonService = Depends(Provide[Container.default_config_service])
):
    """
            function to insert or update default config
        """
    try:
        conf = default_config_service.create_or_update({'task_name': task_name, 'cloud_provider': cloud_provider},
                                                       task_name=task_name, cloud_provider=cloud_provider,
                                                       default_values=default_values)
        response = JSONResponse(content=jsonable_encoder(conf))
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/task_config")
@version(1, 0)
@inject
@validate_license
def delete_default_config(
        task_name: str,
        cloud_provider: str,
        default_config_service: CommonService = Depends(Provide[Container.default_config_service])
):
    """
            function to delete default config
        """
    try:
        conf = default_config_service.delete({'task_name': task_name, 'cloud_provider': cloud_provider})
        response = JSONResponse(content=jsonable_encoder(conf))
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/dropdowns_task_config")
@version(1, 0)
@inject
@validate_license
def get_task_dropdowns(
        name: Optional[str] = 'task_name',
        cloud_provider: Optional[str] = 'All',
        default_config_service: CommonService = Depends(Provide[Container.default_config_service])
):
    """
            function to get all task dropdowns
        """
    try:
        filters = {}
        if cloud_provider != 'All':
            filters['cloud_provider'] = cloud_provider
        data = {'task_name': [], 'cloud_provider': []}

        tasks = default_config_service.fetch_all(filters)
        for task in tasks:
            data['task_name'].append(task.task_name)
            data['cloud_provider'].append(task.cloud_provider)

        resp = list(set(data[name]))
        resp.sort()
        response = JSONResponse(content=jsonable_encoder(resp))


    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/api_config")
@version(1, 0)
@inject
@validate_license
def api_config(
        task_name: str,
        cloud_provider: str,
        application_name: str,
        api_config_service: CommonService = Depends(Provide[Container.api_config_service])
):
    """
            function to get all api config
        """
    try:
        conf = api_config_service.fetch_all(
            {'task_name': task_name, 'cloud_provider': cloud_provider, 'application_name': application_name})
        response = JSONResponse(content=jsonable_encoder(conf))
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/api_config")
@version(1, 0)
@inject
@validate_license
def upsert_api_config(
        config: ApiConfigSchema,
        api_config_service: CommonService = Depends(Provide[Container.api_config_service])
):
    """
            function to insert or update config
    """
    try:
        config = config.dict(exclude_unset=True)
        conf = api_config_service.create_or_update(
            {'task_name': config['task_name'], 'cloud_provider': config['cloud_provider'],
             'application_name': config['application_name']}, **config)
        response = JSONResponse(content=jsonable_encoder(conf))
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/api_config")
@version(1, 0)
@inject
@validate_license
def delete_api_config(
        task_name: str,
        cloud_provider: str,
        application_name: str,
        api_config_service: CommonService = Depends(Provide[Container.api_config_service])
):
    """
            function to delete config data
        """
    try:
        conf = api_config_service.delete(
            {'task_name': task_name, 'cloud_provider': cloud_provider, 'application_name': application_name})
        response = JSONResponse(content=jsonable_encoder(conf))
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/dropdowns_api_config")
@version(1, 0)
@inject
@validate_license
def get_api_dropdowns(
        name: Optional[str] = 'task_name',
        cloud_provider: Optional[str] = 'All',
        api_config_service: CommonService = Depends(Provide[Container.api_config_service])
):
    """
            function to get dropdowns data
        """
    try:
        filters = {}
        if cloud_provider != 'All':
            filters['cloud_provider'] = cloud_provider
        data = {'task_name': [], 'cloud_provider': []}
        tasks = api_config_service.fetch_all(filters)
        for task in tasks:
            data['task_name'].append(task.task_name)
            data['cloud_provider'].append(task.cloud_provider)

        resp = list(set(data[name]))
        resp.sort()
        response = JSONResponse(content=jsonable_encoder(resp))


    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/subcategory")
@version(1, 0)
@inject
@validate_license
def get_subcategory(
        product_category_id: Optional[int],
        cloud_provider: Optional[str],
        product_subcategory_service: CommonService = Depends(Provide[Container.product_subcategory_service]),
        page_no: Optional[int] = 0,
        per_page: Optional[int] = 0
):
    """
            function to get all subcategories
        """
    try:
        resp = {}
        filters = {}
        filters['product_category_id'] = product_category_id
        filters['cloud_provider'] = cloud_provider
        data = product_subcategory_service.fetch_all(filters)
        total = len(data)
        if page_no != 0 and per_page != 0:
            resp['data'] = product_subcategory_service.paginate_fetch(filters, per_page=per_page, page=page_no,
                                                                      total=total)
            resp['total'] = len(data)
        else:
            resp['data'] = data
            resp['total'] = len(data)
        response = JSONResponse(content=jsonable_encoder(resp))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/subcategory")
@version(1, 0)
@inject
@validate_license
def put_product_subcategory(
        product_subcategory: ProductSubCategorySchema,
        product_subcategory_service: CommonService = Depends(Provide[Container.product_subcategory_service])
):
    """
            function to insert or update product subcategory
        """
    product_subcategory = product_subcategory.dict(exclude_unset=True)
    product_subcategory_id = -1
    try:

        if 'id' in product_subcategory:
            product_subcategory_id = product_subcategory['id']
            product_subcategory_detail = product_subcategory_service.fetch({'id': product_subcategory_id})
            product_subcategory_detail = {_col: getattr(product_subcategory_detail, _col) for _col in
                                          product_subcategory_detail.__table__.columns.keys()}
        product_subcategory = product_subcategory_service.create_or_update({'id': product_subcategory_id},
                                                                           **product_subcategory)
        product_subcategory = {_col: getattr(product_subcategory, _col) for _col in
                               product_subcategory.__table__.columns.keys()}
        response = JSONResponse(content=jsonable_encoder(product_subcategory))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/subcategory")
@version(1, 0)
@inject
@validate_license
def delete_subcategory(
        product_subcategory_id: int,
        modified_by: str,
        product_subcategory_service: CommonService = Depends(Provide[Container.product_subcategory_service])
):
    """
            function to delete subcategory
        """
    try:
        product_subcategory = product_subcategory_service.delete({'id': product_subcategory_id})
        if len(product_subcategory) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp = {_col: getattr(product_subcategory[0], _col) for _col in product_subcategory[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:  # pylint: disable=bare-except
            pass
        insert_config_audit_log('category', resp, 'DELETE', modified_by, modified_by)
        product_subcategory.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(product_subcategory))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/category")
@version(1, 0)
@inject
@validate_license
def get_category(
        cloud_provider: Optional[str] = 'All',
        product_category_service: CommonService = Depends(Provide[Container.product_category_service]),
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5
):
    """
            function to get all category
        """
    try:
        filters = {}
        resp = {}
        if cloud_provider != 'All':
            filters['cloud_provider'] = cloud_provider
            data = product_category_service.fetch_all(filters)
            resp = data
        else:
            data = product_category_service.fetch_all(filters)
            total = len(data)
            resp['data'] = product_category_service.paginate_fetch({}, per_page=per_page, page=page_no, total=total)
            resp['total'] = len(data)
        response = JSONResponse(content=jsonable_encoder(resp))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/category")
@version(1, 0)
@inject
@validate_license
def put_product_category(
        product_category: ProductCategorySchema,
        product_category_service: CommonService = Depends(Provide[Container.product_category_service])
):
    """
            function to insert or update product category
        """
    product_category = product_category.dict(exclude_unset=True)
    product_category_id = -1
    try:

        if 'id' in product_category:
            product_category_id = product_category['id']
            product_category_detail = product_category_service.fetch({'id': product_category_id})
            product_category_detail = {_col: getattr(product_category_detail, _col) for _col in
                                       product_category_detail.__table__.columns.keys()}
        product_category = product_category_service.create_or_update({'id': product_category_id}, **product_category)
        product_category = {_col: getattr(product_category, _col) for _col in
                            product_category.__table__.columns.keys()}
        response = JSONResponse(content=jsonable_encoder(product_category))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/category")
@version(1, 0)
@inject
@validate_license
def delete_category(
        product_category_id: int,
        modified_by: str,
        product_category_service: CommonService = Depends(Provide[Container.product_category_service])
):
    """
            function to delete category
        """
    try:
        product_category = product_category_service.delete({'id': product_category_id})
        if len(product_category) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp = {_col: getattr(product_category[0], _col) for _col in product_category[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:  # pylint: disable=bare-except
            pass
        insert_config_audit_log('category', resp, 'DELETE', modified_by, modified_by)
        product_category.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(product_category))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/productitems")
@version(1, 0)
@inject
@validate_license
def get_productitems(
        product_subcategory_id: Optional[int],
        cloud_provider: Optional[str],
        product_items_service: CommonService = Depends(Provide[Container.product_items_service])
):
    """
            function to get product items
        """
    try:
        filters = {}
        filters['product_subcategory_id'] = product_subcategory_id
        filters['cloud_provider'] = cloud_provider
        data = product_items_service.fetch_all(filters)
        response = JSONResponse(content=jsonable_encoder(data))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/productitem")
@version(1, 0)
@inject
@validate_license
def get_productitem(
        id: Optional[int],
        product_item_service: CommonService = Depends(Provide[Container.product_item_service])
):
    """
            function to get single product item
        """
    try:
        filters = {}
        filters['id'] = id
        data = product_item_service.fetch_all(filters)
        response = JSONResponse(content=jsonable_encoder(data))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/productitem")
@version(1, 0)
@inject
@validate_license
def put_product_item(
        product_item: ProductItemSchema,
        product_items_service: CommonService = Depends(Provide[Container.product_items_service])
):
    """
            function to insert product item
    """
    product_item = product_item.dict(exclude_unset=True)
    product_item_id = -1
    try:

        if 'id' in product_item:
            product_item_id = product_item['id']
            product_item_detail = product_items_service.fetch({'id': product_item_id})
            product_item_detail = {_col: getattr(product_item_detail, _col) for _col in
                                   product_item_detail.__table__.columns.keys()}
        product_item = product_items_service.create_or_update({'id': product_item_id}, **product_item)
        product_item = {_col: getattr(product_item, _col) for _col in
                        product_item.__table__.columns.keys()}
        response = JSONResponse(content=jsonable_encoder(product_item))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/productitem")
@version(1, 0)
@inject
@validate_license
def delete_productitem(
        product_item_id: int,
        product_items_service: CommonService = Depends(Provide[Container.product_items_service])
):
    """
            function to delete product item
        """
    try:
        product_item = product_items_service.delete({'id': product_item_id})
        if len(product_item) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp = {_col: getattr(product_item[0], _col) for _col in product_item[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:  # pylint: disable=bare-except
            pass
        # insert_config_audit_log('productitem', resp, 'DELETE', modified_by, modified_by)
        product_item.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(product_item))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/products")
@version(1, 0)
@inject
@validate_license
def get_products(
        resource_adapter_mapping_service: CommonService = Depends(Provide[Container.resource_adapter_mapping_service]),
        product_category_service: CommonService = Depends(Provide[Container.product_category_service])
):
    """
            function to get all products
        """
    try:
        filters = {}
        response = []
        providers = resource_adapter_mapping_service.fetch_all(filters)
        for provider in providers:
            data = {}
            categories = product_category_service.fetch_all({'cloud_provider': provider.cloud_provider})
            data['cloud_provider'] = provider.cloud_provider
            data['screen_name'] = provider.screen_name

            pcatlist = []
            for category in categories:
                pcat = {}
                pcat['id'] = category.id
                pcat['screen_name'] = category.name
                pcatlist.append(pcat)
            data['subcategories'] = pcatlist
            response.append(data)
        response = JSONResponse(content=jsonable_encoder(response))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/user")
@version(1, 0)
@inject
@validate_license
def put_user(
        app_user: AppUserSchema,
        user_service: CommonService = Depends(Provide[Container.user_service])
):
    """
            function to insert or update user
    """
    app_user = app_user.dict(exclude_unset=True)
    user_id = -1
    try:

        if 'user_name' in app_user and app_user['user_name'] is not None:
            app_user['user_name'] = str(app_user['user_name']).lower()
            app_user['email_address'] = str(app_user['user_name']).lower()

        '''
            check if username is alreday exist in the database!
        '''
        if 'id' not in app_user:
            try:
                check_user = user_service.fetch({'user_name': app_user['user_name']})
                check_user = {_col: getattr(check_user, _col) for _col in check_user.__table__.columns.keys()}
                print(check_user)
                if len(check_user) > 0:
                    response = JSONResponse(
                        status_code=500,
                        content="Email address already exist in the system!"
                    )
                    return response
            except:  # pylint: disable=bare-except
                pass
        if 'password' in app_user and app_user['password'] is not None:
            cipher_suite = Fernet(_key)
            encoded_text = cipher_suite.encrypt(bytes(app_user['password'], 'utf-8'))
            app_user['password'] = encoded_text.decode('utf-8')
        if 'id' in app_user:
            user_id = app_user['id']
            user_detail = user_service.fetch({'id': user_id})
            user_detail = {_col: getattr(user_detail, _col) for _col in user_detail.__table__.columns.keys()}
        app_user = user_service.create_or_update({'id': user_id}, **app_user)
        app_user = {_col: getattr(app_user, _col) for _col in app_user.__table__.columns.keys()}
        # insert_config_audit_log('User', app_user, 'PUT',
        #                        app_user['created_by'], app_user['modified_by'])
        response = JSONResponse(content=jsonable_encoder(app_user))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/role")
@version(1, 0)
@inject
@validate_license
def get_roles(
        role_id: Optional[str] = 'All',
        role_service: CommonService = Depends(Provide[Container.role_service]),
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5
):
    """
            function to get all roles
        """
    try:
        resp = {}
        if role_id != 'All':
            app = role_service.fetch({'id': int(role_id)})
            resp['data'] = app
        else:
            apps = role_service.fetch_all({})
            total = len(apps)
            resp['data'] = role_service.paginate_fetch({}, per_page=per_page, page=page_no, total=total)
            resp['total'] = len(apps)
        response = JSONResponse(content=jsonable_encoder(resp))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/role")
@version(1, 0)
@inject
@validate_license
def put_role(
        role: RolesSchema,
        role_service: CommonService = Depends(Provide[Container.role_service])
):
    """
            function to insert or update role
    """
    role = role.dict(exclude_unset=True)
    role_id = -1
    try:
        if 'id' in role:
            role_id = role['id']
            role_detail = role_service.fetch({'id': role_id})
            role_detail = {_col: getattr(role_detail, _col) for _col in role_detail.__table__.columns.keys()}
        role = role_service.create_or_update({'id': role_id, 'name': str(role['name']).lower()}, **role)
        role = {_col: getattr(role, _col) for _col in role.__table__.columns.keys()}
        # insert_config_audit_log('role', role, 'PUT',
        #                        role['created_by'], role['modified_by'])
        response = JSONResponse(content=jsonable_encoder(role))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/role")
@version(1, 0)
@inject
@validate_license
def delete_user(
        role_id: int,
        role_service: CommonService = Depends(Provide[Container.role_service]),
):
    """
            function to delete user
        """
    try:
        role = role_service.delete({'id': role_id})
        if len(role) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp = {_col: getattr(role[0], _col) for _col in role[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:  # pylint: disable=bare-except
            pass
        # insert_config_audit_log('role', resp, 'DELETE', modified_by, modified_by)
        role.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(role))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/userinrole")
@version(1, 0)
@inject
@validate_license
def get_userinroles(
        userrole_id: Optional[str] = 'All',
        user_role_service: CommonService = Depends(Provide[Container.user_role_service]),
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5
):
    """
            function to get user roles
        """
    try:
        resp = {}
        if userrole_id != 'All':
            app = user_role_service.fetch({'id': int(userrole_id)})
            resp['data'] = app
        else:
            apps = user_role_service.fetch_all({})
            total = len(apps)
            resp['data'] = user_role_service.paginate_fetch({}, per_page=per_page, page=page_no, total=total)
            resp['total'] = len(apps)
        response = JSONResponse(content=jsonable_encoder(resp))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.put("/userinrole")
@version(1, 0)
@inject
@validate_license
def put_user_in_role(
        userinrole: UserInRolesSchema,
        user_role_service: CommonService = Depends(Provide[Container.user_role_service])
):
    """
            function to insert or update user roles
        """
    userinrole = userinrole.dict(exclude_unset=True)
    userinrole_id = -1
    try:
        if 'username' in userinrole:
            userinrole['username'] = str(userinrole['username']).lower()

        if 'id' in userinrole:
            userinrole_id = userinrole['id']
            role_detail = user_role_service.fetch({'id': userinrole_id})
            role_detail = {_col: getattr(role_detail, _col) for _col in role_detail.__table__.columns.keys()}
        userinrole = user_role_service.create_or_update(iden_filters={'id': userinrole_id}, **userinrole)
        userinrole = {_col: getattr(userinrole, _col) for _col in userinrole.__table__.columns.keys()}

        # insert_config_audit_log('userinrole', userinrole, 'PUT',
        #                        userinrole['created_by'], userinrole['modified_by'])
        response = JSONResponse(content=jsonable_encoder(userinrole))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/userinrole")
@version(1, 0)
@inject
@validate_license
def delete_user(
        userinrole_id: int,
        user_role_service: CommonService = Depends(Provide[Container.user_role_service]),
):
    """
            function to delete user roles
        """
    try:
        role = user_role_service.delete({'id': userinrole_id})
        if len(role) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp = {_col: getattr(role[0], _col) for _col in role[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:  # pylint: disable=bare-except
            pass
        # insert_config_audit_log('userinrole', resp, 'DELETE', modified_by, modified_by)
        role.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(role))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/isadmin")
@version(1, 0)
@inject
@validate_license
def is_admin(
        username: Optional[str],
        user_role_service: CommonService = Depends(Provide[Container.user_role_service]),
        role_service: CommonService = Depends(Provide[Container.role_service]),
):
    """
            function to return flag role user is admin or not
        """
    try:
        response = {}
        username = str(username).lower()

        admin_rolname = str('Administrator').lower()
        admin_role = role_service.fetch({'name': admin_rolname})
        admin_role = {_col: getattr(admin_role, _col) for _col in admin_role.__table__.columns.keys()}
        user_detail = user_role_service.fetch({'username': username,
                                               'role_id': admin_role.get('id')})
        user_detail = {_col: getattr(user_detail, _col) for _col in user_detail.__table__.columns.keys()}
        if user_detail:
            response['is_admin'] = True
        else:
            response['is_admin'] = False
        json_compatible_execution_data = jsonable_encoder(response)
        response = JSONResponse(content=json_compatible_execution_data)
    except Exception as excp:
        print(excp)
        logger.exception(excp)
        response = JSONResponse(content=dict(is_admin=False))
    return response


@subapi.put("/cloudcred")
@version(1, 0)
@inject
@validate_license
def put_cloud_credentials(
        cloud_credentials: CloudCredentialsSchema,
        cloud_cred_service: CommonService = Depends(Provide[Container.cloud_cred_service]),
        application_service: CommonService = Depends(Provide[Container.application_service])
):
    """
            function to insert or update cloud credentials
    """
    cloud_credentials = cloud_credentials.dict(exclude_unset=True)
    cloud_credentials_id = -1
    try:
        if 'credentials' in cloud_credentials:
            application_details = application_service.fetch({'source': cloud_credentials['source']})
            application_details = {_col: getattr(application_details, _col) for _col in
                                   application_details.__table__.columns.keys()}
            encryption_key = application_details['encryption_key']
            encryption_iv = application_details['encryption_iv']
            credentials = cloud_credentials['credentials']
            _tmp = convert_to_secure(credentials, encryption_key, encryption_iv)
            cloud_credentials['credentials'] = _tmp
        if 'id' in cloud_credentials:
            cloud_credentials_id = cloud_credentials['id']
            cloud_credentials_detail = cloud_cred_service.fetch({'id': cloud_credentials_id})
            cloud_credentials_detail = {_col: getattr(cloud_credentials_detail, _col) for _col in
                                        cloud_credentials_detail.__table__.columns.keys()}
        cloud_credentials = cloud_cred_service.create_or_update({'id': cloud_credentials_id},
                                                                **cloud_credentials)
        cloud_credentials = {_col: getattr(cloud_credentials, _col) for _col in
                             cloud_credentials.__table__.columns.keys()}
        # insert_config_audit_log('cloud_credentials', jsonable_encoder(cloud_credentials), 'PUT',
        #                        cloud_credentials['created_by'], cloud_credentials['modified_by'])
        response = JSONResponse(content=jsonable_encoder(cloud_credentials))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/user")
@version(1, 0)
@inject
@validate_license
def get_user(
        user_name: Optional[str] = 'All',
        user_service: CommonService = Depends(Provide[Container.user_service]),
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5
):
    """
            function to get all user details
        """
    try:
        resp = {}
        if user_name != 'All':
            app = user_service.fetch({'user_name': str(user_name).lower()})
            resp['data'] = app
        else:
            apps = user_service.fetch_all({})
            total = len(apps)
            resp['data'] = user_service.paginate_fetch({},
                                                       per_page=per_page,
                                                       page=page_no,
                                                       total=total)
            resp['total'] = len(apps)
        response = JSONResponse(content=jsonable_encoder(resp))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/user")
@version(1, 0)
@inject
@validate_license
def delete_user(
        user_id: int,
        user_service: CommonService = Depends(Provide[Container.user_service]),
):
    """
            function to delete user
        """
    try:
        user = user_service.delete({'id': user_id})
        if len(user) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp = {_col: getattr(user[0], _col) for _col in user[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:  # pylint: disable=bare-except
            pass
        # insert_config_audit_log('user', resp, 'DELETE', modified_by, modified_by)
        user.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(user))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.delete("/cloudcred")
@version(1, 0)
@inject
@validate_license
def delete_cloudcred(
        cloud_cred_id: int,
        modified_by: str,
        cloud_cred_service: CommonService = Depends(Provide[Container.cloud_cred_service])
):
    """
            function to delete cloud credential
        """
    try:
        cloud_cred = cloud_cred_service.delete({'id': cloud_cred_id})
        if len(cloud_cred) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp={_col: getattr(cloud_cred[0], _col) for _col in cloud_cred[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:  # pylint: disable=bare-except
            pass
        insert_config_audit_log('cloudcred', resp, 'DELETE', modified_by, modified_by)
        cloud_cred.append({'message': 'Success'})
        response = JSONResponse(content=jsonable_encoder(cloud_cred))
    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


@subapi.get("/cloudcred")
@version(1, 0)
@inject
@validate_license
def get_cloudcred(
        cloud_provider: Optional[str] = 'All',
        cloud_cred_service: CommonService = Depends(Provide[Container.cloud_cred_service]),
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5
):
    """
            function to get all cloud credentials
    """
    try:
        filters = {}
        resp = {}
        if cloud_provider != 'All':
            filters['cloud_provider'] = cloud_provider
            data = cloud_cred_service.fetch_all(filters)
            resp = data
        else:
            data = cloud_cred_service.fetch_all(filters)
            total = len(data)
            resp['data'] = cloud_cred_service.paginate_fetch({},
                                                             per_page=per_page,
                                                             page=page_no,
                                                             total=total)
            resp['total'] = len(data)
        response = JSONResponse(content=jsonable_encoder(resp))

    except ValidationError as excp:
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response
