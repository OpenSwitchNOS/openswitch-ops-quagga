from opsvalidator.base import *
from opsvalidator import error
from opsvalidator.error import ValidationError
from opsrest.utils import *
from tornado.log import app_log

# This validator doesn't allow the user to disable ECMP as the support
# would be added in near future

class EcmpValidator(BaseValidator):
    resource = "system"

    def validate_modification(self, validation_args):
        system_row = validation_args.resource_row
        if hasattr(system_row, "ecmp_config"):
            ecmp_config = system_row.__getattr__("ecmp_config")
            enabled_value = ecmp_config.get("enabled", None)
            if enabled_value == "false":
                details = "ECMP cannot be disabled"
                raise ValidationError(error.VERIFICATION_FAILED, details)
