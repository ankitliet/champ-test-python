import re
import json
from functools import wraps

from voluptuous import MultipleInvalid
from voluptuous import error
from . import vm_validation_schema

INVALID_INPUT_TYPE = 1001
MISSING_REQUIRED_FIELD = 1002
INVALID_INPUT = 1003

VALIDATION_CONFIG = {
  "validation_argument": {
    "validation_schema_class": (vm_validation_schema.ValidationSchema),
    "error_codes": {
      "invalid_type": INVALID_INPUT_TYPE,
      "missing_input": MISSING_REQUIRED_FIELD,
      "invalid_input": INVALID_INPUT
    },
    "validation_arguments": {
    }
  }
}


VOLUPTUOUS_ERROR_MESSAGE_PATTERN = {
  "Expected %s value for input %s": \
    (r"^expected (.*?) for dictionary value @ data(.*?)$", "invalid_type"),
  "Missing required input: '%s'": \
    (r"required key not provided @ data\['(.*?)'\]", "missing_input"),
  "Value can not be empty or minimum expected length is %s for %s": \
    ((r"length of value must be at least (\d) for dictionary value @ data"
      "(.*?)$"), "invalid_input"),
  "Invalid input value format for %s": \
    (r"does not match regular expression for dictionary value @ data(.*?)$",
     "invalid_input"),
  "Unsupported value(s) for input %s" : \
    (r"value is not allowed for dictionary value @ data(.*?)$",
     "invalid_input")
}

class Validator(object):

  def __init__(self, **kwargs):
    self.validation_key = "validation_argument"

    self.validation_config = VALIDATION_CONFIG[self.validation_key]
    self.validation_schema_class = \
    self.validation_config["validation_schema_class"]
    self.validation_arguments = self.validation_config["validation_arguments"]


  def make_args(self, input_values):
    """
    :return dict of arguments to be validated.
    """
    args = {}
    for arg, arg_config in self.validation_arguments.items():
      if arg in input_values:
        args[arg] = input_values[arg]
      elif "default_value" in arg_config:
        args[arg] = arg_config["default_value"]
    return args

  def __call__(self, func):
      @wraps(func)
      def _validate_args(*args, **kwargs):
          action_service = kwargs.get("action_service")
          task = kwargs.get("task")
          if not task  or not action_service:
              return func(*args, **kwargs)
          task = task.dict(exclude_unset=True)
          if task:
              action_name = task.get("action")
              cloud_provider = task.get("parameters").get("cloud_provider")
              schema_info = action_service.fetch(iden_filters={
                  'name': action_name, 'cloud_provider': cloud_provider})
              vm_schema = json.loads(schema_info.input_schema)
              if not vm_schema:
                  return func(*args, **kwargs)

              parameter_body = vm_schema.get("body")
              for parameter_name, _ in parameter_body.items():
                  self.validation_arguments[parameter_name] = {}
              self.validation_class_obj = self.validation_schema_class(
                  **self.validation_config)
              validation_schema = \
                  self.validation_class_obj.get_schema(vm_schema)
              args_to_validate = task.get("request_body")
              if args_to_validate:
                  try:
                    validated_arguments = validation_schema(args_to_validate)
                  except MultipleInvalid as mi:
                    for each_error in mi.errors:
                      error_message_dict = mi.msg
                      if isinstance(error_message_dict, (str, str)):
                        for error_msg, pattern in \
                                VOLUPTUOUS_ERROR_MESSAGE_PATTERN.items():
                          matches = re.findall(pattern[0], str(mi), re.M|re.I)
                          if matches:
                            for each_match in matches:
                              error_message_dict = {
                                "message": error_msg % each_match,
                                "error_code": self.validation_class_obj.error_codes.get(
                                  pattern[1])}
                      if isinstance(error_message_dict, (str, str)):
                        error_message_dict = {}
                        error_message_dict["message"] = "Validation error: %s" % str(mi)
                        error_message_dict["error_code"] = \
                          self.validation_class_obj.error_codes.get("invalid_input")
                      if isinstance(each_error, error.RequiredFieldInvalid):
                        error_message_dict["error_code"] = \
                          self.validation_class_obj.error_codes.get("missing_input")
                        raise Exception(error_message_dict)
                      else:
                        raise Exception(error_message_dict)
          return func(*args, **kwargs)
      return _validate_args