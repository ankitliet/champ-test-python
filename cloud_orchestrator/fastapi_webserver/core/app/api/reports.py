import json
import os
import urllib
from urllib.parse import urlparse, parse_qsl, urlencode

import yaml
import logging

from cryptography.fernet import Fernet
from typing import Optional
from core.app.schemas import OAuthProviderSchema, ReportSchema
from util.core.app.validate_license import validate_license

logger = logging.getLogger(__name__)
from pydantic import ValidationError
from core.app.api.dashboard_API import insert_config_audit_log
from core.core.container import Container
from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi_versioning import version
from dependency_injector.wiring import inject, Provide
from starlette.responses import JSONResponse, RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
from core.app.services import CommonService

subapi = APIRouter(prefix='/reports', tags=['Reports'])

with open(os.path.join(os.environ['BASEDIR'], 'core', 'core', 'settings', f'{os.environ["EXECFILE"]}.yml'),
          'r') as file:
    documents = yaml.full_load(file)
_key = bytes(documents['password-encryption']['key'], 'utf-8')


@subapi.put("/report")
@version(1, 0)
@inject
@validate_license
def put_report(
        report: ReportSchema,
        report_service: CommonService = Depends(Provide[Container.report_service])
):
    try:
        report = report.dict(exclude_unset=True)
        modified_by = ''
        if "modified_by" in report:
            modified_by = report['modified_by']
            del report['modified_by']
        report_id = -1
        is_upd = False
        if 'id' in report:
            report_id = report['id']
            is_upd = True
            config_value = report_service.fetch({'id': report_id})
            config_value = {_col: getattr(config_value, _col) for _col in config_value.__table__.columns.keys()}
        oauth = report_service.create_or_update({'id': report_id}, **report)
        oauth = {_col: getattr(oauth, _col) for _col in oauth.__table__.columns.keys()}
        #if is_upd:
        #    insert_config_audit_log('OAuth', oauth, 'UPDATE', modified_by, modified_by)
        response = JSONResponse(content=jsonable_encoder(oauth))
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


@subapi.delete("/report")
@version(1, 0)
@inject
@validate_license
def delete_report(
        report_id: int,
        modified_by: str,
        report_service: CommonService = Depends(Provide[Container.report_service])

):
    try:
        creds = report_service.delete({'id': report_id})
        if len(creds) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp = {_col: getattr(creds[0], _col) for _col in creds[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:
            pass
        #insert_config_audit_log('OAuth', resp, 'DELETE', modified_by, modified_by)
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


@subapi.get("/report")
@version(1, 0)
@inject
@validate_license
def get_reports(
        report_id: Optional[str] = 'All',
        report_service: CommonService = Depends(Provide[Container.report_service])
):
    try:
        if report_id != 'All':
            cred = report_service.fetch({'id': int(report_id)})
            cred = {_col: getattr(cred, _col) for _col in cred.__table__.columns.keys()}
        else:
            cred = report_service.fetch_all({})
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
