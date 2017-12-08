from typing import Dict, List


class RegisterRequestData:
    event_type = 'eventType'
    repository = 'repository'
    job_name = 'jobName'
    labels = 'labels'
    requested_params = 'requested_params'
    branch_restrictions = 'branch_restrictions'
    change_restrictions = 'change_restrictions'
    file_restrictions = 'file_restrictions'

    class RequestedParams:
        branch = 'branch'
        sha = 'sha'
        tag = 'tag'

    @staticmethod
    def __get_mandatory_fields():
        return [RegisterRequestData.event_type,
                RegisterRequestData.repository,
                RegisterRequestData.job_name,
                RegisterRequestData.labels,
                RegisterRequestData.requested_params]

    @staticmethod
    def __has_mandatory_keys(request_data: Dict) -> bool:
        for mandatory_field in RegisterRequestData.__get_mandatory_fields():
            if mandatory_field not in request_data:
                return False
        return True

    @staticmethod
    def __get_allowed_requested_params() -> List[str]:
        return [RegisterRequestData.RequestedParams.branch,
                RegisterRequestData.RequestedParams.sha,
                RegisterRequestData.RequestedParams.tag]

    @staticmethod
    def __are_requested_params_valid(data: Dict):
        for param in data[RegisterRequestData.requested_params]:
            if param not in RegisterRequestData.__get_allowed_requested_params():
                return False
        return True

    @staticmethod
    def is_valid_register_request_data(data: Dict):
        return RegisterRequestData.__has_mandatory_keys(data) and RegisterRequestData.__are_requested_params_valid(data)
