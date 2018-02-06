from typing import Dict, Union, Collection

from app.clients.github_client import GithubClient
from app.enums.event_types import EventType
from app.hook_details.hook_details import HookDetails
from app.mongo.registration_cursor import RegistrationCursor
from app.request_schemes.register_request_data import RegisterRequestData


class ReleaseHookDetails(HookDetails):
    def __repr__(self) -> str:
        return f"<PrOpenedHookDetails " \
               f"repository: {self.repository} " \
               f"tag: {self.tag} " \
               f"release_target: {self.release_target} " \
               f"is_prerelease: {self.is_prerelease} " \
               f">"

    def __init__(self,
                 repository: str,
                 tag: str,
                 release_target: str,
                 is_prerelease: bool) -> None:
        self.repository = repository
        self.tag = tag
        self.release_target = release_target
        self.is_prerelease = is_prerelease

    def get_query(self) -> Dict[str, str]:
        return dict(repository=self.repository)

    def get_allowed_parameters(self) -> Dict[str, Union[str, bool]]:
        return {
            RegisterRequestData.RequestedParams.tag: self.tag,
            RegisterRequestData.RequestedParams.release_target: self.release_target,
            RegisterRequestData.RequestedParams.is_prerelease: self.is_prerelease
        }

    def get_event_type(self) -> EventType:
        return EventType.RELEASE

    def get_ref(self) -> str:
        return self.release_target

    def setup_final_param_values(self, registration_cursor: RegistrationCursor) -> None:
        pass

    async def should_trigger(self, cursor: RegistrationCursor, github_client: GithubClient) -> bool:
        if cursor.file_restrictions and not await github_client.are_files_in_repo(self.repository,
                                                                                  self.release_target,
                                                                                  cursor.file_restrictions):
            return False
        return True
