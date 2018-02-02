from typing import Dict

from app.dto.abstract_hook_details import AbstractHookDetails
from app.enums.event_types import EventTypes
from app.request_schemes.register_request_data import RegisterRequestData


class PrOpenedHookDetails(AbstractHookDetails):
    def __init__(self,
                 repository: str,
                 branch: str,
                 sha: str):
        self.repository = repository
        self.branch = branch
        self.sha = sha

    def get_query(self):
        return dict(repository=self.repository)

    def get_allowed_parameters(self) -> Dict[str, str]:
        return {
            RegisterRequestData.RequestedParams.branch: self.branch,
            RegisterRequestData.RequestedParams.sha: self.sha
        }

    def get_event_type(self) -> str:
        return EventTypes.pr_opened
