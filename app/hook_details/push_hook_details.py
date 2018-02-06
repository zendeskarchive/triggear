from typing import Dict, Set, Union

from app.clients.github_client import GithubClient
from app.enums.event_types import EventType
from app.hook_details.hook_details import HookDetails
from app.mongo.registration_cursor import RegistrationCursor
from app.request_schemes.register_request_data import RegisterRequestData
from app.utilities.functions import get_all_starting_with, any_starts_with


class PushHookDetails(HookDetails):
    def __repr__(self) -> str:
        return f"<PrOpenedHookDetails " \
               f"repository: {self.repository} " \
               f"branch: {self.branch} " \
               f"sha: {self.sha} " \
               f"changes: {self.changes} " \
               f">"

    def __init__(self,
                 repository: str,
                 branch: str,
                 sha: str,
                 changes: Set[str]) -> None:
        self.repository = repository
        self.branch = branch
        self.sha = sha
        self.changes = changes

    def get_changes_as_string(self) -> str:
        return ','.join(self.changes)

    def get_allowed_parameters(self) -> Dict[str, Union[str, bool]]:
        return {
            RegisterRequestData.RequestedParams.branch: self.branch,
            RegisterRequestData.RequestedParams.sha: self.sha,
            RegisterRequestData.RequestedParams.changes: self.get_changes_as_string()
        }

    def get_query(self) -> Dict[str, str]:
        return dict(repository=self.repository)

    def get_event_type(self) -> EventType:
        return EventType.PUSH

    def get_ref(self) -> str:
        return self.sha

    def setup_final_param_values(self, registration_cursor: RegistrationCursor) -> None:
        if registration_cursor.change_restrictions:
            self.changes = get_all_starting_with(self.changes, registration_cursor.change_restrictions)

    async def should_trigger(self, cursor: RegistrationCursor, github_client: GithubClient) -> bool:
        if cursor.change_restrictions and not any_starts_with(any_list=self.changes, starts_with_list=cursor.change_restrictions):
            return False
        elif cursor.branch_restrictions and self.branch not in cursor.branch_restrictions:
            return False
        elif cursor.file_restrictions and not await github_client.are_files_in_repo(self.repository,
                                                                                    self.sha,
                                                                                    cursor.file_restrictions):
            return False
        return True
