from app.clients.github_client import GithubClient
from app.hook_details.release_hook_details import ReleaseHookDetails
from app.mongo.registration_cursor import RegistrationCursor
from app.mongo.triggerable_document import TriggerableDocument


class ReleaseDocument(TriggerableDocument):
    def __init__(self, cursor: RegistrationCursor, github_client: GithubClient):
        self.cursor = cursor
        self.github_client = github_client

    async def should_be_triggered_by(self, hook_details: ReleaseHookDetails) -> bool:
        if self.cursor.file_restrictions and not await self.github_client.are_files_in_repo(hook_details.repository,
                                                                                            hook_details.release_target,
                                                                                            self.cursor.file_restrictions):
            return False
        return True
