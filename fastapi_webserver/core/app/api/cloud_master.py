import base64
import json
import logging
from copy import deepcopy
import adal
import requests
from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_versioning import version

from util.core.app.common import AESCipher
from util.core.app.models import APIConfig as APIConfigurations
from core.app.schemas import CloudmasterSchema
from core.app.services import CommonService
from core.core.container import Container
from util.core.app.validate_license import validate_license

logger = logging.getLogger(__name__)
subapi = APIRouter(prefix='/cloudmaster', tags=['Data master for cloud providers'])


def decrypt_text(decrypt_text, encryption_key, encryption_iv):
    """
                    function to return decrypt text
        """
    _cipher = AESCipher(encryption_key, encryption_iv)
    decrypt_text = _cipher.decrypt(decrypt_text)
    return decrypt_text.decode('utf-8')
    # return decrypt_text


@subapi.post("/info")
@version(1, 0)
@inject
@validate_license
def search(
        cloud_master: CloudmasterSchema,
        cloud_cred_service: CommonService = Depends(Provide[Container.cloud_cred_service]),
        application_service: CommonService = Depends(Provide[Container.application_service]),
):
    """
                    function to to run search query
        """
    try:
        cloud_master = cloud_master.dict(exclude_unset=True)
        if 'credential_id' in cloud_master:
            cloud_credentials_id = cloud_master['credential_id']
            cloud_credentials_detail = cloud_cred_service.fetch({'id': cloud_credentials_id})
            cloud_credentials_detail = {_col: getattr(cloud_credentials_detail, _col) for _col in
                                        cloud_credentials_detail.__table__.columns.keys()}
            cloud_master['credentials'] = cloud_credentials_detail.get('credentials')

        application_details = application_service.fetch({'source': cloud_master['source']})
        application_details = {_col: getattr(application_details, _col) for _col in
                               application_details.__table__.columns.keys()}
        encryption_key = application_details['encryption_key']
        encryption_iv = application_details['encryption_iv']

        _cipher = AESCipher(encryption_key, encryption_iv)
        cloud_master = recr_dict(cloud_master, _cipher.decrypt)

        response = execute(cloud_master['task_name'], cloud_master, cloud_cred_service.get_session())
    except Exception as excp:
        logger.exception(excp)
        json_compatible_resp = jsonable_encoder(dict(error=excp.__str__()))
        response = JSONResponse(
            status_code=500,
            content=json_compatible_resp
        )
    return response


def execute(func_name, parameters, session, **kwargs):
    """
                    function to ----
        """
    try:
        response_array = []
        logger.debug(f"{func_name}:{parameters}")
        apimeta = fetch_apimeta(
            cloud_provider=parameters.get('cloud_provider'),
            source=parameters.get('source'),
            task_name=func_name,
            session=session
        )
        data = deepcopy(apimeta['request_parameters'])
        for key, value in apimeta['request_parameters_map'].items():
            tmp = deepcopy(parameters)
            for val in value:
                tmp = tmp[val]
            data[key] = tmp
        resp = hit(
            method=apimeta['method'],
            url=apimeta['request_url'],
            headers=apimeta.get('headers', {}),
            data=data,
            parameters=parameters
        )
        tmp = deepcopy(resp)['value']

        for jtmp in tmp:
            response = {}
            if isinstance(jtmp, dict):
                for key, value in apimeta['response_parameters_map'].items():
                    for val in value:
                        _value = jtmp[val]
                        response[key] = _value
                response_array.append(response)
        return response_array
    except Exception as excp:
        logger.exception("Exception %s", excp.__repr__())
        raise excp


def fetch_apimeta(cloud_provider: str, source: str, task_name: str, session):
    """
                    function to get all api metadata
        """
    with session() as session:
        meta = session.query(
            APIConfigurations
        ).where(
            APIConfigurations.application_name.__eq__(
                source
            )
        ).where(
            APIConfigurations.task_name.__eq__(
                task_name
            )
        ).where(
            APIConfigurations.cloud_provider.__eq__(
                cloud_provider
            )
        ).one()
        logger.debug(f"PostProvisiong[{source}] metainfo[{meta._asdict().__repr__()}]")
        if not meta.request_url:
            raise Exception("IPAM url is missing:%s" % task_name)
        return meta._asdict()


def hit(method: str, url: str, headers={}, data={}, parameters={}):
    """
         function to identify method type
    """
    logger.debug("URL: %s, Payload:%s" % (url, data))
    resp = {}
    endpoint = eval(url)
    if method == 'GET':
        method_name = parameters.get('cloud_provider') + "_get"
        resp = eval(method_name)(endpoint, parameters)
    elif method == 'POST':
        resp = requests.post(url, headers=headers, data=json.dumps(data),
                             verify=False)
    elif method == 'PUT':
        resp = requests.put(url, headers=headers, data=json.dumps(data),
                            verify=False)
    return resp


def azure_get(url, parameters):
    """
                    function to authorize azure credentials
        """
    credentials = parameters.get('credentials')
    authentication_endpoint = 'https://login.microsoftonline.com/'
    resource = 'https://management.core.windows.net/'

    # get an Azure access token using the adal library
    context = adal.AuthenticationContext(authentication_endpoint + credentials.get('azure_tenant_id'))
    token_response = context.acquire_token_with_client_credentials \
        (resource, credentials.get('azure_client_id'),
         credentials.get('azure_client_secret'))

    access_token = token_response.get('accessToken')
    headers = {"Authorization": 'Bearer ' + access_token}
    response = requests.get(url, headers=headers, verify=False).json()
    print(response)
    return response


def recr_dict(_dict, func):
    """
        function to --
    """
    _tmp = deepcopy(_dict)
    for key, value in _dict.items():
        if isinstance(value, dict):
            _tmp[key] = recr_dict(value, func)
        elif isinstance(value, str):
            if key.startswith('__e__'):
                _value = func(_tmp.pop(key))
                _tmp[key.strip('__e__')] = _value.strip()
            else:
                _tmp[key] = value.strip()
    return _tmp
