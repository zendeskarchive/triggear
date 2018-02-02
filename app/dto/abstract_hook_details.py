from typing import List, Dict, Optional

from app.utilities.functions import item_starting_with_from_list


class AbstractHookDetails:
    def get_event_type(self) -> str:
        raise NotImplementedError()

    def get_allowed_parameters(self) -> Dict[str, str]:
        raise NotImplementedError()

    def get_query(self):
        raise NotImplementedError()

    def get_requested_parameters_values(self, requested_parameters: List[str]) -> Optional[Dict[str, str]]:
        job_params = None
        if requested_parameters:
            job_params = {}
            for param in requested_parameters:
                allowed_parameter = item_starting_with_from_list(param, set(self.get_allowed_parameters().keys()))
                if allowed_parameter is not None:
                    requested_param_name = self._get_parsed_param_key(allowed_parameter, param)
                    job_params[requested_param_name] = self.get_allowed_parameters()[allowed_parameter]
        return job_params if job_params != {} else None

    @staticmethod
    def _get_parsed_param_key(prefix, param):
        return prefix if param == prefix else param.split(':', 1)[1]
