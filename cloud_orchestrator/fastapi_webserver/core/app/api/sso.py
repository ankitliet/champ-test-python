import json
import os
import urllib
from urllib.parse import urlparse, parse_qsl, urlencode

import yaml
import logging

from cryptography.fernet import Fernet
from typing import Optional
from core.app.schemas import OAuthProviderSchema
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

subapi = APIRouter(prefix='/sso', tags=['SSO Configuration'])
oauthapi = APIRouter(prefix='/oauth', tags=['OAuth Configuration'])

with open(os.path.join(os.environ['BASEDIR'], 'core', 'core', 'settings', f'{os.environ["EXECFILE"]}.yml'),
          'r') as file:
    documents = yaml.full_load(file)
_key = bytes(documents['password-encryption']['key'], 'utf-8')


def decrypt_password(decrypt_text):
    """
                function to return decrypt password
        """
    cipher_suite = Fernet(_key)
    _pass = bytes(decrypt_text, 'utf-8')
    decode_text = cipher_suite.decrypt(_pass)
    return decode_text.decode('utf-8')


def oauth_register(oauth_detail):
    """
                function to register oauth
    """
    oauth = OAuth()
    oauth.register(
        name='provider',
        client_id=oauth_detail.client_id,
        client_secret=decrypt_password(oauth_detail.client_secret),
        server_metadata_url=oauth_detail.config_url,
        client_kwargs={
            'scope': 'openid email profile',
        }
    )
    return oauth


@subapi.get('/login')
@version(1, 0)
@inject
# @validate_license
async def login(
        request: Request,
        oauth_service: CommonService = Depends(Provide[Container.oauth_service])
):
    """
                function to login in the application
        """
    provider = request.query_params.get('provider')
    redirect_uri = request.url_for('auth')
    request.session['oauth_provider'] = request.query_params.get('provider')
    oauth_detail = oauth_service.fetch({'provider': provider})
    oauth = oauth_register(oauth_detail)
    return await oauth.provider.authorize_redirect(request, redirect_uri)


@subapi.get('/auth')
@version(1, 0)
@inject
# @validate_license
async def auth(
        request: Request,
        oauth_service: CommonService = Depends(Provide[Container.oauth_service]),
):
    """
                function to get auth data
        """
    error_url = "/error"
    try:
        oauth_detail = oauth_service.fetch({'provider': request.session['oauth_provider']})
        error_url = oauth_detail.app_error_url
        oauth = oauth_register(oauth_detail)
        token = await oauth.provider.authorize_access_token(request)
        user = token.get('userinfo')
        if user:
            request.session['userinfo'] = dict(user)
        print(user)
    except Exception as error:
        print(error)
        json_compatible_resp = jsonable_encoder(error)
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
        return RedirectResponse(url=error_url)
    except OAuthError as error:
        print(error)
        json_compatible_resp = jsonable_encoder(error)
        response = JSONResponse(
            status_code=401,
            content=json_compatible_resp
        )
        return RedirectResponse(url=error_url)

    # response = JSONResponse(content=jsonable_encoder(user))
    _userinfo = dict(user)
    print(_userinfo)
    redirect_url = "{}?{}".format(oauth_detail.app_home_url, urlencode(_userinfo))
    print(redirect_url)
    return RedirectResponse(url=redirect_url)


@oauthapi.put("/oauth")
@version(1, 0)
@inject
@validate_license
def put_credentials(
        oauth: OAuthProviderSchema,
        oauth_service: CommonService = Depends(Provide[Container.oauth_service])
):
    """
                function to insert or update credentials oauth
        """
    try:
        oauth = oauth.dict(exclude_unset=True)
        modified_by = ''
        if "modified_by" in oauth:
            modified_by = oauth['modified_by']
            del oauth['modified_by']
        if oauth['client_secret'] is not None:
            # encoded_text = base64.b64encode(bytes(oauth['client_secret'], 'utf-8'))
            cipher_suite = Fernet(_key)
            encoded_text = cipher_suite.encrypt(bytes(oauth['client_secret'], 'utf-8'))
            oauth['client_secret'] = encoded_text.decode('utf-8')
        oauth_id = -1
        is_upd = False
        config_value = {}
        if 'id' in oauth:
            oauth_id = oauth['id']
            is_upd = True
            config_value = oauth_service.fetch({'id': oauth_id})
            config_value = {_col: getattr(config_value, _col) for _col in config_value.__table__.columns.keys()}
        oauth = oauth_service.create_or_update({'id': oauth_id}, **oauth)
        oauth = {_col: getattr(oauth, _col) for _col in oauth.__table__.columns.keys()}
        # if is_upd:
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


@oauthapi.delete("/oauth")
@version(1, 0)
@inject
@validate_license
def delete_credentials(
        oauth_id: int,
        modified_by: str,
        oauth_service: CommonService = Depends(Provide[Container.oauth_service])

):
    """
                function to delete oauth credentials
        """
    try:
        creds = oauth_service.delete({'id': oauth_id})
        if len(creds) == 0:
            response = JSONResponse(content=jsonable_encoder({}))
            return response
        resp = {_col: getattr(creds[0], _col) for _col in creds[0].__table__.columns.keys()}
        try:
            del resp['created_date']
            del resp['modified_date']
        except:
            pass
        # insert_config_audit_log('OAuth', resp, 'DELETE', modified_by, modified_by)
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


@oauthapi.get("/oauth")
@version(1, 0)
@inject
@validate_license
def get_credentials(
        oauth_id: Optional[str] = 'All',
        oauth_service: CommonService = Depends(Provide[Container.oauth_service])
):
    """
                function to get all credentials data
        """
    try:
        creds = oauth_service.fetch_all({})
        cred = []
        for c in creds:
            x = {_col: getattr(c, _col) for _col in c.__table__.columns.keys()}
            if 'client_secret' in x:
                x['client_secret'] = decrypt_password(x['client_secret'])
                cred.append(x)
        if oauth_id != 'All':
            cred = oauth_service.fetch({'id': int(oauth_id)})
            cred = {_col: getattr(cred, _col) for _col in cred.__table__.columns.keys()}
            if 'client_secret' in cred:
                cred['client_secret'] = decrypt_password(cred['client_secret'])
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
