from voluptuous import All, Any, Range, Required, Schema, Boolean, Coerce, \
  Length, REMOVE_EXTRA, In, ALLOW_EXTRA, MultipleInvalid, MatchInvalid, Object
from voluptuous.validators import Replace

MISSING_INPUT_SEARCH_ERROR_MSG = "Missing required input: 'search'"
INVALID_INPUT_SEARCH_ERROR_MSG = "Expected str or unicode value for 'search'"
MISSING_INPUT_FS_ERROR_MSG = "Missing required input: 'file_server_uuid'"
INVALID_INPUT_FS_ERROR_MSG = ("Expected str or unicode value for "
                              "'file_server_uuid'")
MISSING_INPUT_BUCKETS_ERROR_MSG = "Missing required input: 'buckets'"
INVALID_INPUT_BUCKETS_ERROR_MSG = "Invalid value of 'buckets'"
MISSING_INPUT_OPERATIONS_ERROR_MSG = "Missing required input: 'operations'"
INVALID_OPERATIONS_ERROR_MSG = "Invalid value of 'operations'"

class BaseValidator(object):
  # Base validation schema class
  def __init__(self, validation_arguments, *args, **kwargs):
    self.validation_config = validation_arguments
    self.error_codes = kwargs.get("error_codes", {})
    super(BaseValidator, self).__init__(*args)

  def get_schema(self, validate_schema):
    """
    :param validation_config(dict): validation configuration
    :return schema object for the respective class.
    """
    # Construct error message with provided error code(if any) and error message
    error_message = {
      "error_code": self.error_codes.get("missing_input"),
      "message": self.error_codes.get(
        "missing_error_message", ("Missing required input: 'user_name'"))}

    schema_params = {}
    return schema_params

class ValidationSchema(BaseValidator):
  """Test Validation schema.
  """
  def __init__(self, *args, **kwargs):
    super(ValidationSchema, self).__init__(*args, **kwargs)

  def get_schema(self, validate_schema):
    """schema object for the respective class.
    """
    schema_params = {}
    for parameter_name, type in validate_schema.get("body").items():
        if "list" in type.lower():
            schema_params.update({Required(parameter_name): All(list)})
        elif "string" in type.lower():
            schema_params.update({Required(parameter_name): Any(str, None)})
        elif "int" in type.lower():
            schema_params.update({Required(parameter_name): All(Coerce(int))})
        elif "bool" in type.lower():
            schema_params.update({Required(parameter_name): Any(Boolean(), None)})
        elif "dict" in type.lower():
            schema_params.update({Required(parameter_name): All(dict)})
        elif "object" in type.lower():
            schema_params.update({Required(parameter_name): All(object)})
        else:
            raise Exception("Invalid parameter type")

    schema_params.update(super(
      ValidationSchema, self).get_schema(validate_schema))
    return Schema(schema_params)