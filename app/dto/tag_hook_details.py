from typing import Dict

from app.dto.abstract_hook_details import AbstractHookDetails
from app.enums.event_types import EventTypes
from app.request_schemes.register_request_data import RegisterRequestData


class TagHookDetails(AbstractHookDetails):
    def __init__(self,
                 repository: str,
                 sha: str,
                 tag: str):
        self.repository = repository
        self.sha = sha
        self.tag = tag

    def get_query(self):
        return dict(repository=self.repository)

    def get_allowed_parameters(self) -> Dict[str, str]:
        return {
            RegisterRequestData.RequestedParams.tag: self.tag,
            RegisterRequestData.RequestedParams.sha: self.sha
        }

    def get_event_type(self) -> str:
        return EventTypes.pr_opened
