import json
import jsonschema
from jsonschema import validate
from functools import wraps


class JValidator(object):

    def __init__(self, **kwargs):
        self.service_name = kwargs.get('service_name')

    def get_schema(self, task, action_service):
        action = action_service.fetch({'name': task['blueprint_name'], 'cloud_provider': task['cloud_provider']})
        schema = json.loads(action.input_schema)
        # print(schema)
        return schema

    def __call__(self, func):
        @wraps(func)
        def validate_json(*args, **kwargs):
            service = kwargs.get(self.service_name)
            task = kwargs.get('task')
            task = task.dict(exclude_unset=True)
            if not task or not service:
                return func(*args, **kwargs)
            execute_api_schema = self.get_schema(task, service)
            try:
                validate(instance=json.loads(json.dumps(task)), schema=execute_api_schema)
            except jsonschema.exceptions.ValidationError as err:
                print(err)
                return err

            return func(*args, **kwargs)

        return validate_json
