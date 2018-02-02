import pytest
from mockito import mock, expect

from app.clients.github_client import GithubClient
from app.enums.event_types import EventType
from app.hook_details.pr_opened_hook_details import PrOpenedHookDetails
from app.mongo.registration_cursor import RegistrationCursor
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestPrOpenedHookDetails:
    async def test__repr(self):
        assert f"{PrOpenedHookDetails('repo', 'master', '123321')}" \
               == "<PrOpenedHookDetails repository: repo, branch: master, sha: 123321 >"

    async def test__get_query(self):
        assert PrOpenedHookDetails('repo', 'master', '123321').get_query() == {'repository': 'repo'}

    async def test__get_allowed_parameters(self):
        assert PrOpenedHookDetails('repo', 'master', '123321').get_allowed_parameters() \
               == {'branch': 'master', 'sha': '123321'}

    async def test__get_ref(self):
        assert PrOpenedHookDetails('repo', 'master', '123321').get_ref() == '123321'

    async def test__setup_final_params(self):
        registration_cursor = mock(spec=RegistrationCursor, strict=True)
        PrOpenedHookDetails('repo', 'master', '123321').setup_final_param_values(registration_cursor)

    async def test__should_trigger__with_file_restrictions(self):
        github_client = mock(spec=GithubClient, strict=True)

        registration_cursor = mock({'file_restrictions': [], 'branch_restrictions': []}, spec=RegistrationCursor, strict=True)
        assert await PrOpenedHookDetails('repo', 'master', '123321').should_trigger(registration_cursor, github_client)

        registration_cursor = mock({'file_restrictions': ['README.md'], 'branch_restrictions': []}, spec=RegistrationCursor, strict=True)
        expect(github_client).are_files_in_repo('repo', '123321', ['README.md']).thenReturn(async_value(False))
        assert not await PrOpenedHookDetails('repo', 'master', '123321').should_trigger(registration_cursor, github_client)

        registration_cursor = mock({'file_restrictions': ['README.md'], 'branch_restrictions': []}, spec=RegistrationCursor, strict=True)
        expect(github_client).are_files_in_repo('repo', '123321', ['README.md']).thenReturn(async_value(True))
        assert await PrOpenedHookDetails('repo', 'master', '123321').should_trigger(registration_cursor, github_client)

    async def test__should_trigger__with_branch_restrictions(self):
        github_client = mock(spec=GithubClient, strict=True)

        registration_cursor = mock({'file_restrictions': [], 'branch_restrictions': ['master', 'staging']}, spec=RegistrationCursor, strict=True)
        assert await PrOpenedHookDetails('repo', 'master', '123321').should_trigger(registration_cursor, github_client)

        registration_cursor = mock({'file_restrictions': [], 'branch_restrictions': ['sandbox', 'staging']}, spec=RegistrationCursor, strict=True)
        assert not await PrOpenedHookDetails('repo', 'master', '123321').should_trigger(registration_cursor, github_client)

    async def test__get_event_type(self):
        assert PrOpenedHookDetails('repo', 'master', '123321').get_event_type() == EventType.PR_OPENED
