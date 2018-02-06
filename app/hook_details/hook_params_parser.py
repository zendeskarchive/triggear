from typing import Optional, Dict, Union

from app.hook_details.hook_details import HookDetails
from app.mongo.registration_cursor import RegistrationCursor
from app.utilities.functions import item_starting_with_from_list


class HookParamsParser:
    @staticmethod
    def get_requested_parameters_values(hook_details: HookDetails,
                                        registration_cursor: RegistrationCursor) -> Optional[Dict[str, Union[str, bool]]]:
        job_params = None
        if registration_cursor.requested_params:
            job_params = {}
            for param in registration_cursor.requested_params:
                allowed_parameter = item_starting_with_from_list(param, set(hook_details.get_allowed_parameters().keys()))
                if allowed_parameter is not None:
                    requested_param_name = HookParamsParser._get_parsed_param_key(allowed_parameter, param)
                    job_params[requested_param_name] = hook_details.get_allowed_parameters()[allowed_parameter]
        return job_params if job_params != {} else None

    @staticmethod
    def _get_parsed_param_key(prefix: str,
                              param: str) -> str:
        return prefix if param == prefix else param.split(':', 1)[1]
