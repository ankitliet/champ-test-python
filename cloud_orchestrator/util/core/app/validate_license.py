import json
import logging
import os
import yaml
import requests
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

from .resources import DatabaseResource
from .repositories import CommonRepository
from .services import CommonService
from util.core.app.models import DBConfigModel
from functools import wraps

logger = logging.getLogger(__name__)


def validate_license(func):
    @wraps(func)
    async def wrap_func(*args, **kwargs):
        response = {}
        config_file = os.path.join(os.environ['BASEDIR'],
                                   'configurations',
                                   f'{os.environ["EXECFILE"]}.yml')

        if not os.path.exists(config_file):
            config_file = os.path.join(os.environ['BASEDIR'],
                                       'core', 'core', 'settings',
                                       f'{os.environ["EXECFILE"]}.yml')

        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
        except Exception as ex:
            raise Exception("Config file not found:%s" % str(ex))

        db = DatabaseResource(
            db_url=config.get('db').get('url'),
            db_schema=config.get('db').get('schema')
        )

        try:
            session_factory = db.session
            service = CommonService(repository=CommonRepository(session_factory,
                                                                DBConfigModel))
            details = service.fetch(iden_filters={'key': 'license_key'})
            details = {_col: getattr(details, _col) for _col in details.__table__.columns.keys()}

            source = config.get('champ').get('source')
            license_details = json.loads(details.get('value'))

            headers = {
                        "X-SOURCE-KEY": source,
                        "X-API-KEY": license_details['api_key'],
                        "Content-Type": "application/json"
                      }

            license_api = service.fetch(iden_filters={'key': 'license_api'})
            license_api = {_col: getattr(license_api, _col) for _col in license_api.__table__.columns.keys()}

            url = license_api['value']. \
                format(license_details['customer_id'], license_details['license_key'])

            resp = requests.get(url, headers=headers, verify=False)
            print(resp)
            if resp.status_code == 200:
                logger.debug("You have valid license")
            else:
                logger.error("You have invalid license")
                logger.error(json.loads(resp.content))
                raise Exception(json.loads(resp.content))

        except Exception as error:
            print(error)
            json_compatible_resp = jsonable_encoder(dict(msg=error.__str__()))
            response = JSONResponse(
                status_code=500,
                content=json_compatible_resp
            )
            return response

        return func(*args, **kwargs)
    return wrap_func
