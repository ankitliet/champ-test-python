import requests
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_versioning import version
from dependency_injector.wiring import inject, Provide
from pydantic import ValidationError
import jsonschema
import os
import yaml
import pytz

from util.core.app.config_audit import insert_config_audit
from core.app.schemas import *
from core.core.container import Container
from core.handlers.jenkins_handler.queuehandler import MessageQueue
from core.app.api.dashboard_API import get_queues
from core.app.services import *
from core.utils.common import update_nested_dict
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS, MAINTAINANCE_MODE
from util.core.app.add_default_config import add_default_config
from util.core.app.email_client import send_email
from util.core.app.validate_license import validate_license

subapi = APIRouter(prefix='/orchestrator', tags=['Task triggering'])
admin_subapi = APIRouter(prefix='/admin', tags=['Admin Tasks'])
notification_subapi = APIRouter(prefix='/notification', tags=['Notification Tasks'])
freshservice_subapi = APIRouter(prefix='/freshservice', tags=['freshservice Tasks'])


def get_portal_url():
    """
        function to get portal url
        """
    with open(os.path.join(os.environ['BASEDIR'], 'core', 'core', 'settings', f'{os.environ["EXECFILE"]}.yml'),
              'r') as file:
        config = yaml.full_load(file)
    return config["teams"]["portal_url"]


def get_source():
    """
        function to get source
        """
    with open(os.path.join(os.environ['BASEDIR'], 'core', 'core', 'settings', f'{os.environ["EXECFILE"]}.yml'),
              'r') as file:
        config = yaml.full_load(file)
    return config["champ"]["source"]


def get_team_webhook_url():
    """
        function to get team webhook url
        """
    with open(os.path.join(os.environ['BASEDIR'], 'core', 'core', 'settings', f'{os.environ["EXECFILE"]}.yml'),
              'r') as file:
        config = yaml.full_load(file)
    return config["teams"]["team_webhook_url"]


with open(os.path.join(os.environ['BASEDIR'], 'core', 'core', 'settings', f'{os.environ["EXECFILE"]}.yml'),
          'r', errors="ignore") as file:
    documents = yaml.full_load(file)
_exclude_list = documents['response_list']['exclude']

from util.core.app.logger import get_logger_func

logger = get_logger_func(__file__)


def insert_config_audit_log(config_name, value, Operation, created_by, modified_by):
    """
        function to insert config audit log
    """
    payload = {
        "config_name": config_name,
        "config_value": value,
        "operation_name": Operation,
        "created_by": created_by,
        "modified_by": modified_by

    }
    insert_config_audit(payload)


@subapi.put("/task")
@version(1, 0)
@inject
@validate_license
# @JValidator(service_name='auto_action_service')
def create_or_update_auto_task(
        task: AutoTaskSchema,
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service]),
        auto_plan_service: CommonService = Depends(Provide[Container.auto_plan_service]),
        state_trans_service: CommonService = Depends(Provide[Container.state_trans_service]),
        rmq_service: MessageQueue = Depends(Provide[Container.rmq_service]),
        dbconfig_service: CommonService = Depends(Provide[Container.dbconfig_service]),
        cloud_cred_service: CommonService = Depends(Provide[Container.cloud_cred_service])
):
    """
            function to create or update auto task
        """
    payload = {
        "task_id": "",
        "source": "API",
        "event": "CreateTask",
        "status": TASK_STATUS.COMPLETED,
        "timestamp": datetime.utcnow(),
        "trace": ""
    }
    task = task.dict(exclude_unset=True)
    if 'task_id' in task:
        task_id = task.get('task_id')
    else:
        task_id = uuid().hex
    try:
        logger.debug("TASK api call:%s" % task, {'task_id': task_id})
        _conf = dbconfig_service.fetch(iden_filters={'key': 'maintenance_flag'})
        if _conf.value == 'ACTIVE':
            logger.debug("Maintenance flag is up", {'task_id': task_id})
            excp = HTTPException(status_code=404, detail="Maintanence is going on, please try again later :)")
            logger.exception(excp, {'task_id': task_id})
            resp = {"status": TASK_STATUS.FAILED,
                    "response": {"message": "Maintanence is going on, please try again later :)"}}
            json_compatible_resp = jsonable_encoder(resp)
            response = JSONResponse(
                status_code=404,
                content=json_compatible_resp
            )
            payload.update({
                "task_id": task_id,
                "trace": str(excp)
            })
            insert_audit_log(payload)
            return response
        # task = task.dict(exclude_unset=True)
        if 'cloud_credentials_id' in task['parameters']:
            cloud_credentials = cloud_cred_service.fetch_all({'id': task['parameters']['cloud_credentials_id']})
            for cloud_red in cloud_credentials:
                task['parameters'].update(cloud_red.credentials)

        if 'task_id' not in task:
            task['parameters']['blueprint_name'] = task['task_name'] = task.pop('blueprint_name')
            task['parameters']['cloud_provider'] = task['cloud_provider']
            task['parameters']['cust_sub_id'] = task.pop('cust_sub_id')
        last_state = None
        if 'task_id' in task:
            logger.debug("Retry the task:%s" % task, {'task_id': task_id})
            fetched_task = auto_task_service.fetch(
                iden_filters={'task_id': task['task_id']}
            )
            fetched_task = {_col: getattr(fetched_task, _col) for _col in fetched_task.__table__.columns.keys()}
            status = fetched_task.pop('status')
            if not status == 'FAILED':
                if status == 'SUCCESS':
                    raise Exception(
                        f'Task[{fetched_task["task_id"]}] has been completed successfully, Cannot initiate retry!!!!')
                else:
                    raise Exception(f'Task[{fetched_task["task_id"]}] is currently under progress, kindly retry later.')
            else:
                task = auto_task_service.create_or_update(
                    iden_filters={'task_id': task['task_id']},
                    status='FAILED',
                    **task
                )
                task = {_col: getattr(task, _col) for _col in task.__table__.columns.keys()}
                _plan = \
                    state_trans_service.fetch_all(
                        iden_filters={'plan_id': task['task_id'], 'current_status': 'FAILED'})[0]

                # TODO update json encoder and decoder
                task['created_date'] = str(task['created_date'])
                task['modified_date'] = str(task['modified_date'])
                task = update_nested_dict(_plan.payload, task)
                last_state = _plan.current_state
        else:
            logger.debug("Create new task:%s" % task, {'task_id': task_id})
            task = auto_task_service.create_or_update(
                iden_filters=None,
                task_id=task_id,
                status='FAILED',
                **task
            )
            task = {_col: getattr(task, _col) for _col in task.__table__.columns.keys()}
            task['parameters']['deployment_id'] = task_id
            task['created_date'] = str(task['created_date'])
            task['modified_date'] = str(task['modified_date'])

        task_type = auto_action_service.fetch(
            {'task_name': task['task_name'], 'cloud_provider': task['cloud_provider']})
        plan = auto_plan_service.fetch({'id': task_type.plan_id, 'cloud_provider': task['cloud_provider']})
        plan = plan.execution_plan

        logger.debug("Main plan is:%s" % plan)
        external_plans = None
        if 'external_plans' in plan.get('StateTransition'):
            external_plans = plan.get('StateTransition').pop('external_plans')
        if external_plans:
            for i in range(len(external_plans)):
                each_external_plan = external_plans[i]
                task_type = auto_action_service.fetch(
                    {'task_name': each_external_plan, 'cloud_provider': task['cloud_provider']})
                sub_plan = auto_plan_service.fetch({'id': task_type.plan_id,
                                                    'cloud_provider': task['cloud_provider']})
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
        task['task_type_id'] = task_type.id
        plan['PlanId'] = task_id
        plan['Payload'] = task
        task = add_default_config(task)
        logger.debug("Updated task:%s" % task, {'task_id': task_id})
        if last_state is not None:
            plan["LastExecutionIndex"] = last_state
        logger.debug("Insert task in queue", {'task_id': task_id})
        queue_data = get_queues(page_no=1, per_page=100)
        print("queue_data={}".format(queue_data))
        queue_data_json = json.loads(queue_data.body.decode('utf-8'))
        for qdj in queue_data_json['data']:
            print(qdj)
            if task['cloud_provider'] in qdj['mapping_names']:
                queue_name = qdj['queue_name']
                exchange_key = qdj['exchange_key']
                break
            elif qdj['is_default']:
                queue_name = qdj['queue_name']
                exchange_key = qdj['exchange_key']
        print(task['cloud_provider'])
        print('!!!!!!!!!!!!!!!!!!!!!!!')
        response = rmq_service.insert_task(body=json.dumps(plan), queue_name=queue_name, exchange_key=exchange_key,
                                           queue=task['cloud_provider'])
        logger.debug("Task inserted in queue", {'task_id': task_id})
        auto_task_service.create_or_update(
            iden_filters={'task_id': task_id},
            status='IN_QUEUE',
        )
        task['status'] = 'IN_QUEUE'
        task['response'] = response
        payload.update({
            "task_id": task_id,
            "status": TASK_STATUS.COMPLETED,
            "trace": "Request Received and in queue!"
        })
        json_compatible_resp = task
        response = JSONResponse(content=jsonable_encoder(json_compatible_resp))
        logger.debug("Response is:%s" % response, {'task_id': task_id})

    except ValidationError as excp:
        logger.debug("Exception is:%s" % str(excp), {'task_id': task_id})
        resp = {"status": TASK_STATUS.FAILED, "response": {"message": excp.__str__}}
        json_compatible_resp = jsonable_encoder(resp)
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
        payload.update({
            "task_id": task_id,
            "trace": excp.json()
        })
    except jsonschema.exceptions.ValidationError as excp:
        logger.debug("Exception is:%s" % str(excp), {'task_id': task_id})
        logger.exception(excp)
        resp = {"status": TASK_STATUS.FAILED, "response": {"message": excp.__str__}}
        json_compatible_resp = jsonable_encoder(resp)
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
        payload.update({
            "task_id": task_id,
            "trace": str(excp)
        })
    except Exception as excp:
        logger.debug("Exception is:%s" % str(excp), {'task_id': task_id})
        logger.exception(excp)
        resp = {"status": TASK_STATUS.FAILED, "response": {"message": excp.__str__}}
        json_compatible_resp = jsonable_encoder(resp)
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
        payload.update({
            "task_id": task_id,
            "trace": str(excp)
        })

    finally:
        insert_audit_log(payload)
    return response


#     return True


@subapi.put("/task/{cloud_provider}/{task_name}")
@version(1, 0)
@inject
@validate_license
# @JValidator(service_name='auto_action_service')
def create_or_update_auto_task_test(
        cloud_provider: str,
        task_name: str,
        task: AutoTaskSchema,
):
    """
            function to create or update auto task test
        """
    response = create_or_update_auto_task(task)
    return response


@subapi.put("/rollback")
@version(1, 0)
@inject
@validate_license
# @JValidator(service_name='auto_action_service')
def create_or_update_auto_task_rollback(
        task: AutoTaskSchema,
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        auto_action_service: CommonService = Depends(Provide[Container.auto_action_service]),
        auto_plan_service: CommonService = Depends(Provide[Container.auto_plan_service]),
        state_trans_service: CommonService = Depends(Provide[Container.state_trans_service]),
        rmq_service: MessageQueue = Depends(Provide[Container.rmq_service]),
        dbconfig_service: CommonService = Depends(Provide[Container.dbconfig_service])
):
    """
            function to create or update auto task rollback
        """
    payload = {
        "task_id": "",
        "source": "API",
        "event": "CreateTask",
        "status": TASK_STATUS.COMPLETED,
        "timestamp": datetime.utcnow(),
        "trace": ""
    }
    task = task.dict(exclude_unset=True)
    if 'task_id' in task:
        task_id = task.get('task_id')
    else:
        raise Exception('Invalid Request!')
    logger.debug("RollBack api call:%s" % task, {'task_id': task_id})
    try:
        _conf = dbconfig_service.fetch(iden_filters={'key': 'maintenance_flag'})
        if _conf.value == 'ACTIVE':
            raise HTTPException(status_code=404, detail="Maintanence is going on, please try again later :)")

        task['parameters']['blueprint_name'] = task['task_name'] = task.pop('blueprint_name')
        task['parameters']['cloud_provider'] = task['cloud_provider']
        task['parameters']['cust_sub_id'] = task.pop('cust_sub_id')
        last_state = None
        if 'task_id' in task:
            fetched_task = auto_task_service.fetch(
                iden_filters={'task_id': task['task_id']}
            )
            fetched_task = {_col: getattr(fetched_task, _col) for _col in fetched_task.__table__.columns.keys()}
            status = fetched_task.pop('status')
            if not status == 'FAILED':
                if status == 'SUCCESS':
                    raise Exception(
                        f'Task[{fetched_task["task_id"]}] has been completed successfully, Cannot initiate rollback!!!!')
                else:
                    raise Exception(f'Task[{fetched_task["task_id"]}] is currently under progress, kindly retry later.')
            else:
                task = auto_task_service.create_or_update(
                    iden_filters={'task_id': task['task_id']},
                    status='FAILED', rollback=True,
                    **task
                )
                task = {_col: getattr(task, _col) for _col in task.__table__.columns.keys()}
                _plan = \
                    state_trans_service.fetch_all(
                        iden_filters={'plan_id': task['task_id'], 'current_status': 'FAILED'})[0]

                # TODO update json encoder and decoder
                task['created_date'] = str(task['created_date'])
                task['modified_date'] = str(task['modified_date'])
                task = update_nested_dict(_plan.payload, task)
                last_state = _plan.current_state
        else:
            raise Exception('Invalid Request!')

        task_type = auto_action_service.fetch(
            {'task_name': task['task_name'], 'cloud_provider': task['cloud_provider']})
        plan = auto_plan_service.fetch({'id': task_type.plan_id, 'cloud_provider': task['cloud_provider']})
        plan = plan.execution_plan
        task['task_type_id'] = task_type.id
        plan['PlanId'] = task['task_id']
        plan['Payload'] = task
        last_rollback_state = plan['StateTransition'][last_state].get('rollback')
        if last_rollback_state == None:
            raise Exception(f'Cannot initiate rollback from state[{last_state}]')
        plan["LastExecutionIndex"] = last_rollback_state
        logger.debug("RollBack task insert in queue", {'task_id': task_id})
        response = rmq_service.insert_task(body=json.dumps(plan), queue=task['cloud_provider'])
        logger.debug("RollBack task inserted in queue", {'task_id': task_id})
        auto_task_service.create_or_update(
            iden_filters={'task_id': task['task_id']},
            status='IN_QUEUE',
        )
        task['status'] = 'IN_QUEUE'
        task['response'] = response
        payload.update({
            "task_id": task['task_id'],
            "status": TASK_STATUS.COMPLETED,
            "trace": "Request Received and in queue!"
        })
        json_compatible_resp = task
        response = JSONResponse(content=jsonable_encoder(json_compatible_resp))
    except HTTPException as excp:
        logger.debug("Exception is:%s" % str(excp), {'task_id': task_id})
        raise excp
    except ValidationError as excp:
        logger.debug("Exception is:%s" % str(excp), {'task_id': task_id})
        json_compatible_resp = jsonable_encoder(excp.errors())
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
        payload.update({
            "task_id": task.get('task_id', ''),
            "trace": excp.json()
        })
    except jsonschema.exceptions.ValidationError as excp:
        logger.debug("Exception is:%s" % str(excp), {'task_id': task_id})
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
        payload.update({
            "task_id": task.get('task_id', ''),
            "trace": str(excp)
        })
    except Exception as excp:
        logger.debug("Exception is:%s" % str(excp), {'task_id': task_id})
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
        payload.update({
            "task_id": task.get('task_id', ''),
            "trace": str(excp)
        })

    finally:
        insert_audit_log(payload)
    return response


@subapi.get("/response")
@version(1, 0)
@inject
@validate_license
def get_callback_response(
        task_id: Optional[str] = None,
        audit_log_service: CommonService = Depends(Provide[Container.audit_log_service]),
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        states_service: CommonService = Depends(Provide[Container.states_service])
):
    """
            function to get all callback response details
        """
    try:
        logger.debug("Response api call")
        data = {}
        filters = {}
        if task_id != None:
            filters['task_id'] = task_id
        requests = auto_task_service.fetch_all(filters)
        if len(requests) == 0:
            data = {'error': 'No such request'}
            response = JSONResponse(status_code=404, content=jsonable_encoder(data))
            return response
        request = requests[0]
        data['status'] = request.status
        data['message'] = ''
        if data['status'] != TASK_STATUS.FAILED:
            data['message'] = data['status']
        else:
            logs = audit_log_service.fetch_all({'task_id': request.task_id})
            for x in logs:
                source = x.source.lower()
                if 'callback' in source:
                    continue
                if x.status == TASK_STATUS.FAILED:
                    data['message'] = x.trace
                    break
        data['details'] = {}
        data['details']['task_id'] = request.task_id
        data['details']['references'] = request.references
        data['details']['task_name'] = request.task_name
        data['details']['source'] = request.source
        data['details']['cloud_provider'] = request.cloud_provider
        data['details']['resources'] = []
        logger.debug("Response details are:%s" % data, {'task_id': request.task_id})

        # if data['status'] == TASK_STATUS.COMPLETED:
        # We need to collect resource info even if provisioning failed for one
        # of the resource.
        states = states_service.fetch_like({'task_id': request.task_id})
        for x in states:
            output = json.loads(x.data)
            data['details']['resources'] = data['details']['resources'] + output['resources']
        exclude_list = _exclude_list.split(',')
        remove_values = []
        for x in data['details']['resources']:
            if 'type' in x:
                if x['type'] in exclude_list:
                    remove_values.append(x)

        for x in remove_values:
            data['details']['resources'].remove(x)

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


@admin_subapi.put("/sys_config")
@version(1, 0)
@inject
@validate_license
def create_or_update_sys_config(
        key: str,
        value: str,
        modified_by: str,
        dbconfig_service: CommonService = Depends(Provide[Container.dbconfig_service])
):
    """
            function to create or update sys config
        """
    try:
        try:
            db_value = dbconfig_service.fetch(iden_filters={'key': key})
            db_value = {_col: getattr(db_value, _col) for _col in db_value.__table__.columns.keys()}
            insert_config_audit_log('System Config({})'.format(key), db_value, 'UPDATE', modified_by, modified_by)

        except Exception as excp:
            pass

        if key == 'maintenance_flag':
            value = value.upper()
            values = set(item.value for item in MAINTAINANCE_MODE)
            if value not in values:
                raise Exception('Please Enter the following values for maintenance_flag {}'.format(values))
        resp = dbconfig_service.create_or_update(
            iden_filters={'key': key},
            key=key,
            value=value
        )
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


@admin_subapi.get("/sys_config")
@version(1, 0)
@inject
@validate_license
def get_sys_config(
        dbconfig_service: CommonService = Depends(Provide[Container.dbconfig_service])
):
    """
            function to get system configration
        """
    try:
        resp = dbconfig_service.fetch_all(iden_filters={})
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


@subapi.post("/transactions")
@version(1, 0)
@inject
@validate_license
def get_ref_search(
        conditions: Jeopardy,
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
        state_trans_service: CommonService = Depends(Provide[Container.state_trans_service]),
        page_no: Optional[int] = 1,
        per_page: Optional[int] = 5
):
    """
            function to insert transaction
        """
    try:
        filters = {}
        resp = {}
        for k, v in conditions.filters.items():
            filters[k] = v
        data, total = auto_task_service.references_search(iden_filters=filters, per_page=per_page, page=page_no)
        data1 = []
        identifiers = state_trans_service.get_identifier({})
        df = pd.DataFrame(identifiers, columns=['task_id', 'identifier', 'timestamp'])
        df = df.sort_values('timestamp')
        df = df.drop_duplicates(subset="task_id", keep='first')
        df = df.set_index('task_id')
        # print(df)

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
                    d1['identifier'] = df.loc[d1['task_id']].identifier
            except:
                pass
            data1.append(d1)
        resp['data'] = data1
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


@notification_subapi.post("/teams_webhook")
@version(1, 0)
@inject
@validate_license
def champ_callback(
        request: CallbackResponseSchema,
):
    """
            function to insert teams webhook
        """
    try:
        url = get_team_webhook_url()
        headers = {
            'Content-Type': 'application/json'
        }
        # json_param = dict(response=request.json())
        json_content = {
            "themeColor": "00FF00" if request.status == "SUCCESS" else "#FF0000",
            "summary": "Automated Notification",
            "sections": [{
                "activityTitle": "<{}> {} : Automated Notification for Task ID - {}". \
                    format(request.details.get("task_name"), request.status,
                           request.details.get("task_id")),
                "activitySubtitle": "Automation Execution for Transaction ID <b> {} </b> is <b> {} </b>. \
                Please check the below transaction details and update the customer. \
                If you have subscribed for AzureDevOps, ticket has been opened for \
                the failure transaction for tracking purpose.".format(request.details.get("task_id"), request.status),
                "facts": [{
                    "name": "Source",
                    "value": request.details.get("source")
                }, {
                    "name": "Task Id",
                    "value": request.details.get("task_id")
                }, {
                    "name": "Task Name",
                    "value": request.details.get("task_name")
                }, {
                    "name": "Status",
                    "value": request.status
                }, {
                    "name": "Cloud Provider",
                    "value": request.details.get("cloud_provider")
                }, {
                    "name": "Error Message",
                    "value": request.message
                }],
                "markdown": True
            }],
            "potentialAction": [{
                "@type": "OpenUri",
                "name": "View Transaction",
                "targets": [{
                    "os": "default",
                    "uri": get_portal_url().format(
                        request.details.get("task_id"))
                }]
            }]
        }
        response = requests.post(url, headers=headers, data=json.dumps(json_content))
        response = response.text.encode('utf8')
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


@notification_subapi.post("/email")
@version(1, 0)
@inject
@validate_license
def email_notification(
        request: CallbackResponseSchema,
        application_service: CommonService = Depends(Provide[Container.application_service]),
        auto_task_service: CommonService = Depends(Provide[Container.auto_task_service]),
):
    """
            function to send email notification
        """
    try:
        application_details = application_service.fetch({'source': request.details.get('source')})
        application_details = {_col: getattr(application_details, _col) for _col in
                               application_details.__table__.columns.keys()}
        email_channel = application_details.get('channel').get('channel').get('emailsettings')
        task_details = auto_task_service.fetch({'task_id': request.details.get('task_id')})
        task_details = {_col: getattr(task_details, _col) for _col in
                        task_details.__table__.columns.keys()}
        kwargs = {
            "api_url": get_portal_url().format(
                request.details.get("task_id")),
            "task_id": request.details.get("task_id"),
            "task_name": request.details.get('task_name'),
            "source": request.details.get('source'),
            "references": request.details.get("references"),
            "cloud_provider": request.details.get("cloud_provider"),
            "status": request.status,
            "message": request.message
        }
        send_email(email_channel.get('host'), email_channel.get('port'), \
                   email_channel.get('from_addr'), task_details.get('created_by'), \
                   email_channel.get('cc_addr'), email_channel.get('username'), email_channel.get('password'), **kwargs)
        response = "Success"
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


@notification_subapi.post("/devops_createtask")
@version(1, 0)
@inject
@validate_license
def azuredevops_workitem(
        request: CallbackResponseSchema,
        application_service: CommonService = Depends(Provide[Container.application_service]),
):
    """
            function to insert azure devops workitem
        """
    try:
        application_details = application_service.fetch({'source': request.details.get('source')})
        application_details = {_col: getattr(application_details, _col) for _col in
                               application_details.__table__.columns.keys()}
        devops_channel = application_details.get('channel').get('channel').get('devops_createtask')
        kwargs = {
            "api_url": get_portal_url().format(
                request.details.get("task_id")),
            "task_id": request.details.get("task_id"),
            "task_name": request.details.get('task_name'),
            "source": request.details.get('source'),
            "references": request.details.get("references"),
            "cloud_provider": request.details.get("cloud_provider"),
            "status": request.status,
            "message": request.message
        }
        data = [
            {
                "op": "add",
                "path": "/fields/System.Title",
                "value": f'Automation Task - {request.details.get("task_id")} - [FAILED]'
            },
            {
                "op": "add",
                "path": "/fields/System.Description",
                "value": json.dumps(kwargs)
            }
        ]
        resp = requests.post(
            devops_channel.get('uri'), json=data,
            headers={'Content-Type': 'application/json-patch+json'},
            auth=('', devops_channel.get('token'))
        )
        # resp.raise_for_status()
        response = resp.json()
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


@freshservice_subapi.post("/ticket")
@version(1, 0)
@inject
@validate_license
def resolve_ticket(
        request: CallbackResponseSchema,
        application_service: CommonService = Depends(Provide[Container.application_service]),
):
    """
            function to create ticket
        """
    try:
        application_details = application_service.fetch({'source': request.details.get('source')})
        application_details = {_col: getattr(application_details, _col) for _col in
                               application_details.__table__.columns.keys()}
        freshservice = application_details.get('channel').get('channel').get('freshservice')

        api_key = freshservice.get("api_key")
        password = freshservice.get("password")
        base_url = freshservice.get("url")
        if request.status == "FAILED":
            description = 'Automation Request via CHAMP integration has been failed. <br/> <b>Automation Task ID ' \
                          ':</b> {} <br/> <b>Error Message :</b> {}'. \
                format(request.details.get("task_id"), request.message)
            status = 3
        else:
            description = 'Automation Request via CHAMP integration is Success. <br/> <b>Automation Task ID :</b> {}'. \
                format(request.details.get("task_id"))
            status = 5
        '''
            Update Freshservice ticket description and status
        '''
        data = {
            "status": status,
            "description": description
        }
        ticket_id = request.details.get("references").get("ticket_id")
        r = requests.put(
            "{}/api/v2/tickets/{}".format(base_url, ticket_id), json=data,
            headers={'Content-Type': 'application/json'},
            auth=(api_key, password))

        if r.status_code == 200:
            logger.debug("Request for updating freshservice ticket processed successfully")
            response = json.loads(r.content)
        else:
            logger.debug("Failed to update the freshservice tickets. Error message : {}".format(r.content))
            response = json.loads(r.content)
            return response
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


@freshservice_subapi.get("/ticket")
@version(1, 0)
@inject
@validate_license
def get_ticket(
        ticket_id: str,
        source: str = 'CloudOrch',
        application_service: CommonService = Depends(Provide[Container.application_service]),
):
    """
            function to get ticket
        """
    try:
        application_details = application_service.fetch({'source': source})
        application_details = {_col: getattr(application_details, _col) for _col in
                               application_details.__table__.columns.keys()}
        freshservice = application_details.get('channel').get('channel').get('freshservice')

        api_key = freshservice.get("api_key")
        password = freshservice.get("password")
        base_url = freshservice.get("url")

        r = requests.get("{}/api/v2/tickets/{}".format(base_url, ticket_id),
                         auth=(api_key, password))

        if r.status_code == 200:
            print("Request processed successfully, the response is given below")
            print(r.content)
            response = json.loads(r.content)
        else:
            print("Failed to read tickets, errors are displayed below,")
            print(r.content)
            response = json.loads(r.content)
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


@freshservice_subapi.get("/asset_types")
@version(1, 0)
@inject
@validate_license
def get_asset_types(
        source: str = 'CloudOrch',
        asset_type_id: str = 'All',
        application_service: CommonService = Depends(Provide[Container.application_service]),
):
    """
            function to get all asset types
        """
    try:
        application_details = application_service.fetch({'source': source})
        application_details = {_col: getattr(application_details, _col) for _col in
                               application_details.__table__.columns.keys()}
        freshservice = application_details.get('channel').get('channel').get('freshservice')

        api_key = freshservice.get("api_key")
        password = freshservice.get("password")
        base_url = freshservice.get("url")
        if asset_type_id != 'All':
            r = requests.get("{}/api/v2/asset_types/{}/fields".format(base_url, asset_type_id),
                             auth=(api_key, password))
        else:
            r = requests.get("{}/api/v2/asset_types".format(base_url),
                             auth=(api_key, password))
        if r.status_code == 200:
            print("Request processed successfully, the response is given below")
            print(r.content)
            response = json.loads(r.content)
        else:
            print("Failed to read tickets, errors are displayed below,")
            print(r.content)
            response = json.loads(r.content)
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


@freshservice_subapi.get("/assets")
@version(1, 0)
@inject
@validate_license
def get_assets(
        source: str = 'CloudOrch',
        application_service: CommonService = Depends(Provide[Container.application_service]),
):
    """
            function to get assets
        """
    try:
        application_details = application_service.fetch({'source': source})
        application_details = {_col: getattr(application_details, _col) for _col in
                               application_details.__table__.columns.keys()}
        freshservice = application_details.get('channel').get('channel').get('freshservice')

        api_key = freshservice.get("api_key")
        password = freshservice.get("password")
        base_url = freshservice.get("url")
        r = requests.get("{}/api/v2/assets?include=type_fields".format(base_url),
                         auth=(api_key, password))

        if r.status_code == 200:
            print("Request processed successfully, the response is given below")
            print(r.content)
            response = json.loads(r.content)
        else:
            print("Failed to read tickets, errors are displayed below,")
            print(r.content)
            response = json.loads(r.content)
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


def create_freshservice_assets(data, base_url, api_key, password):
    """
            function to create freshservice assets
        """
    r = requests.post(
        "{}/api/v2/assets".format(base_url), json=data,
        headers={'Content-Type': 'application/json'},
        auth=(api_key, password))

    if r.status_code == 200:
        logger.debug("Request for creating freshservice assets processed successfully")
        response = json.loads(r.content)
    else:
        logger.debug("Failed to create the freshservice assets. Error message : {}".format(r.content))
        print(r)
        response = json.loads(r.content)
    return response


def get_azure_asset_info(champ_response, asset_types):
    """
            function to get azure asset info
        """
    data = {}
    type_fields = {}
    for asset_type in asset_types['asset_types']:
        '''
        if asset_type['name'] == 'Cloud':
            type_fields["provider_type_{}".format(asset_type['id'])] = "AZURE"
            for resource in champ_response.details.get('resources'):
                if resource['type'] == "azurerm_virtual_machine":
                    for instance in resource.get("instances"):
                        type_fields["region_{}".format(asset_type['id'])] = \
                            instance.get("attributes").get("location")
        '''

        if asset_type['name'] == 'Virtual Machine':
            for resource in champ_response.details.get('resources'):
                if resource['type'] == "azurerm_network_interface":
                    for instance in resource.get("instances"):
                        type_fields["private_address_{}".format(asset_type['id'])] = \
                            instance.get("attributes").get("private_ip_address")
                if resource['type'] == "azurerm_public_ip":
                    for instance in resource.get("instances"):
                        type_fields["public_address_{}".format(asset_type['id'])] = \
                            instance.get("attributes").get("fqdn")
                if resource['type'] == "azurerm_virtual_machine":
                    for instance in resource.get("instances"):
                        type_fields["item_id_{}".format(asset_type['id'])] = \
                            instance.get("attributes").get("id")
                        type_fields["item_name_{}".format(asset_type['id'])] = \
                            instance.get("attributes").get("name")
                        type_fields["os_name_{}".format(asset_type['id'])] = \
                            instance.get("attributes").get("storage_image_reference")[0]["offer"]
        if asset_type['name'] == 'Azure VM':
            data["asset_type_id"] = asset_type["id"]
            for resource in champ_response.details.get('resources'):
                if resource['type'] == "azurerm_virtual_machine":
                    for instance in resource.get("instances"):
                        type_fields["resource_uri_{}".format(asset_type['id'])] = \
                            instance.get("attributes").get("id")
                        type_fields["publisher_{}".format(asset_type['id'])] = \
                            instance.get("attributes").get("storage_image_reference")[0]["publisher"]
                        type_fields["offer_{}".format(asset_type['id'])] = \
                            instance.get("attributes").get("storage_image_reference")[0]["offer"]
                        type_fields["sku_{}".format(asset_type['id'])] = \
                            instance.get("attributes").get("storage_image_reference")[0]["sku"]
                        type_fields["os_disk_name_{}".format(asset_type['id'])] = \
                            instance.get("attributes").get("storage_os_disk")[0]["name"]
                        type_fields["computer_name_{}".format(asset_type['id'])] = \
                            instance.get("attributes").get("name")
                        data["name"] = \
                            instance.get("attributes").get("name")
    data["type_fields"] = type_fields
    print(data)
    return data


@freshservice_subapi.post("/assets")
@version(1, 0)
@inject
@validate_license
def create_assets(
        champ_response: CallbackResponseSchema,
        application_service: CommonService = Depends(Provide[Container.application_service]),
):
    """
            function to create assets
        """
    try:
        response = {"status": "Success"}
        application_details = application_service.fetch({'source': champ_response.details.get('source')})
        application_details = {_col: getattr(application_details, _col) for _col in
                               application_details.__table__.columns.keys()}
        freshservice = application_details.get('channel').get('channel').get('freshservice')

        api_key = freshservice.get("api_key")
        password = freshservice.get("password")
        base_url = freshservice.get("url")

        if champ_response.status != "FAILED":
            r = requests.get("{}/api/v2/asset_types".format(base_url),
                             auth=(api_key, password))
            if r.status_code == 200:
                print("Request processed successfully, the response is given below")
                asset_types = json.loads(r.content)
                if champ_response.details.get('cloud_provider') == 'azure' and \
                        champ_response.details.get('task_name').__contains__('provisioning'):
                    data = get_azure_asset_info(champ_response, asset_types)
                    response = create_freshservice_assets(data, base_url, api_key, password)

        return response

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


@subapi.get("/license")
@version(1, 0)
@inject
def get_license(
        dbconfig_service: CommonService = Depends(Provide[Container.dbconfig_service])
):
    """
            function to get license
    """
    try:
        license_key = dbconfig_service.fetch({'key': 'license_key'})
        license_key = {_col: getattr(license_key, _col) for _col in
                       license_key.__table__.columns.keys()}
        license_key = json.loads(license_key.get('value'))

        license_details = dbconfig_service.fetch({'key': 'license_details'})
        license_details = {_col: getattr(license_details, _col) for _col in
                           license_details.__table__.columns.keys()}
        source = get_source()
        headers = {
            "X-SOURCE-KEY": source,
            "X-API-KEY": license_key['api_key'],
            "Content-Type": "application/json"
        }

        url = license_details['value']. \
            format(license_key['customer_id'], license_key['license_key'])

        resp = requests.get(url, headers=headers, verify=False)
        response = json.loads(resp.content)

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
