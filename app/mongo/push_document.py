from app.clients.github_client import GithubClient
from app.hook_details.push_hook_details import PushHookDetails
from app.mongo.registration_cursor import RegistrationCursor
from app.mongo.triggerable_document import TriggerableDocument
from app.utilities.functions import any_starts_with


class PushDocument(TriggerableDocument):
    def __init__(self, cursor: RegistrationCursor, github_client: GithubClient) -> None:
        self.cursor = cursor
        self.github_client = github_client

    async def should_be_triggered_by(self, hook_details: PushHookDetails) -> bool:
        if self.cursor.change_restrictions and not any_starts_with(any_list=hook_details.changes, starts_with_list=self.cursor.change_restrictions):
            return False
        elif self.cursor.branch_restrictions and hook_details.branch not in self.cursor.branch_restrictions:
            return False
        elif self.cursor.file_restrictions and not await self.github_client.are_files_in_repo(hook_details.repository,
                                                                                              hook_details.sha,
                                                                                              self.cursor.file_restrictions):
            return False
        return True
