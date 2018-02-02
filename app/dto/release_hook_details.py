from typing import Dict

from app.dto.abstract_hook_details import AbstractHookDetails
from app.enums.event_types import EventTypes
from app.request_schemes.register_request_data import RegisterRequestData


class ReleaseHookDetails(AbstractHookDetails):
    def __init__(self,
                 repository: str,
                 tag: str,
                 release_target: str,
                 is_prerelease: bool):
        self.repository = repository
        self.tag = tag
        self.release_target = release_target
        self.is_prerelease = is_prerelease

    def get_query(self):
        return dict(repository=self.repository)

    def get_allowed_parameters(self) -> Dict[str, str]:
        return {
            RegisterRequestData.RequestedParams.tag: self.tag,
            RegisterRequestData.RequestedParams.release_target: self.release_target,
            RegisterRequestData.RequestedParams.is_prerelease: self.is_prerelease
        }

    def get_event_type(self) -> str:
        return EventTypes.pr_opened
