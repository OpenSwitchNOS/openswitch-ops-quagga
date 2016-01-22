from opsvalidator.base import *
from opsvalidator import error
from opsvalidator.error import ValidationError
from opsrest.utils import *
from tornado.log import app_log


class BgpRouterValidator(BaseValidator):
    resource = "bgp_router"

    def validate_modification(self, validation_args):
        is_new = validation_args.is_new
        vrf_row = validation_args.p_resource_row

        if is_new:
            bgp_routers = utils.get_column_data_from_row(vrf_row,
                                                         "bgp_routers")

            # Since working on the IDL that already has the reflective change,
            # the total number of bgp_routers in parent table can be used
            # to validate allowed bgp_routers.
            if bgp_routers is not None:
                if len(bgp_routers) > 1:
                    details = "Only one BGP router can be created"
                    raise ValidationError(error.RESOURCES_EXCEEDED, details)

        app_log.debug('Validation Successful')
