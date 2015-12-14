from opsvalidator.base import *
from opsvalidator import error
from opsvalidator.error import ValidationError
from opsrest.utils import *
from tornado.log import app_log


class BgpRouterValidator(BaseValidator):
    resource = "bgp_router"

    def validate_create(self, validation_args):
        config_data = validation_args.config_data
        vrf_resource = validation_args.p_resource
        vrf_row = validation_args.p_resource_row

        bgp_routers = utils.get_column_data_from_row(vrf_row,
                                                     vrf_resource.column)

        if bgp_routers is not None:
            for asn in bgp_routers:
                if asn != config_data["asn"]:
                    code = error.RESOURCES_EXCEEDED
                    details = "Another BGP with ASN %d already exists" % asn
                    raise ValidationError(error.RESOURCES_EXCEEDED, details)

        app_log.debug('Validation Successful')
