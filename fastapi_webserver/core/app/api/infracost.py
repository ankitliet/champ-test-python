import logging

#from util.core.app.cipher_keys import AESCipher
from util.core.app.validate_license import validate_license

logger = logging.getLogger(__name__)
import os
import yaml
from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_versioning import version
from dependency_injector.wiring import inject, Provide
from pydantic import ValidationError
from core.core.container import Container
from core.app.services import *

cost_api = APIRouter(prefix='/infracost', tags=['Infracost APIs'])

def get_config():
    with open(os.path.join(os.environ['BASEDIR'], 'core', 'core', 'settings', f'{os.environ["EXECFILE"]}.yml'),
              'r') as file:
        config = yaml.full_load(file)
    return config

@cost_api.get("/infracost")
@version(1, 0)
@inject
@validate_license
def get_cost(
        task_id: str,
        infracost_service: CommonService = Depends(Provide[Container.infracost_service])
):
    try:
        search = "{}%".format(task_id)
        # print(search)
        infracost = infracost_service.fetchlike_by_taskid({'task_id': task_id})
        #infracost = {_col: getattr(infracost, _col) for _col in
        #                       infracost.__table__.columns.keys()}
        response = infracost

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

def create_dir(task_id:str, path: str) -> None:
    '''
    : Creates a directory if it does not exist

    : params:
        : path[str]: The directory path as to which the directory has to be created
    '''
    try:
        logger.debug("Create Dir:%s" % path, {'task_id': task_id})
        os.mkdir(path)
    except FileExistsError as excp:
        logger.exception(excp, {'task_id': task_id})
        logger.warning(f'The dir[{path}] already exists! Hence skipping!',
                             {'task_id': task_id})
