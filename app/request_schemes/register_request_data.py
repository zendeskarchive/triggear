from typing import Dict, List

from app.utilities.functions import starts_with_item_from_list


class RegisterRequestData:
    jenkins_url = 'jenkins_url'
    event_type = 'eventType'
    repository = 'repository'
    job_name = 'jobName'
    labels = 'labels'
    requested_params = 'requested_params'
    branch_restrictions = 'branch_restrictions'
    change_restrictions = 'change_restrictions'
    file_restrictions = 'file_restrictions'

    class RequestedParams:
        changes = 'changes'
        branch = 'branch'
        sha = 'sha'
        tag = 'tag'
        release_target = 'release_target'
        is_prerelease = 'is_prerelease'
        who = 'who'
        pr_url = 'pr_url'

    @staticmethod
    def __get_mandatory_fields() -> List[str]:
        return [RegisterRequestData.event_type,
                RegisterRequestData.repository,
                RegisterRequestData.job_name,
                RegisterRequestData.labels,
                RegisterRequestData.requested_params,
                RegisterRequestData.jenkins_url]

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
                RegisterRequestData.RequestedParams.tag,
                RegisterRequestData.RequestedParams.changes,
                RegisterRequestData.RequestedParams.release_target,
                RegisterRequestData.RequestedParams.is_prerelease,
                RegisterRequestData.RequestedParams.who,
                RegisterRequestData.RequestedParams.pr_url]

    @staticmethod
    def __get_allowed_requested_params_prefixes() -> List[str]:
        return [param + ':' for param in RegisterRequestData.__get_allowed_requested_params()]

    @staticmethod
    def __are_requested_params_valid(data: Dict) -> bool:
        for param in data[RegisterRequestData.requested_params]:
            if param not in RegisterRequestData.__get_allowed_requested_params() \
                    and not starts_with_item_from_list(param, RegisterRequestData.__get_allowed_requested_params_prefixes()):
                return False
        return True

    @staticmethod
    def is_valid_register_request_data(data: Dict) -> bool:
        return RegisterRequestData.__has_mandatory_keys(data) and RegisterRequestData.__are_requested_params_valid(data)
