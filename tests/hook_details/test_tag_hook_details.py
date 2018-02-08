import pytest
from mockito import mock, expect

from app.clients.github_client import GithubClient
from app.enums.event_types import EventType
from app.hook_details.tag_hook_details import TagHookDetails
from app.mongo.registration_cursor import RegistrationCursor
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestTagHookDetails:
    async def test__repr(self):
        assert f"{TagHookDetails('repo', '123321', '1.0')}" \
               == "<TagHookDetails repository: repo, tag: 1.0, sha: 123321 >"

    async def test__get_query(self):
        assert TagHookDetails('repo', '123321', '1.0').get_query() == {'repository': 'repo'}

    async def test__get_allowed_parameters(self):
        assert TagHookDetails('repo', '123321', '1.0').get_allowed_parameters() \
               == {'sha': '123321', 'tag': '1.0'}

    async def test__get_ref(self):
        assert TagHookDetails('repo', '123321', '1.0').get_ref() == '123321'

    async def test__setup_final_params(self):
        registration_cursor = mock(spec=RegistrationCursor, strict=True)
        TagHookDetails('repo', '123321', '1.0').setup_final_param_values(registration_cursor)

    async def test__should_trigger(self):
        github_client = mock(spec=GithubClient, strict=True)

        registration_cursor = mock({'file_restrictions': []}, spec=RegistrationCursor, strict=True)
        assert await TagHookDetails('repo', '123321', '1.0').should_trigger(registration_cursor, github_client)

        registration_cursor = mock({'file_restrictions': ['README.md']}, spec=RegistrationCursor, strict=True)
        expect(github_client).are_files_in_repo('repo', '123321', ['README.md']).thenReturn(async_value(False))
        assert not await TagHookDetails('repo', '123321', '1.0').should_trigger(registration_cursor, github_client)

        registration_cursor = mock({'file_restrictions': ['README.md']}, spec=RegistrationCursor, strict=True)
        expect(github_client).are_files_in_repo('repo', '123321', ['README.md']).thenReturn(async_value(True))
        assert await TagHookDetails('repo', '123321', '1.0').should_trigger(registration_cursor, github_client)

    async def test__get_event_type(self):
        assert TagHookDetails('repo', '123321', '1.0').get_event_type() == EventType.TAGGED
