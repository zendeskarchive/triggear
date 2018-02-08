import pytest
from mockito import mock, expect

from app.clients.github_client import GithubClient
from app.enums.event_types import EventType
from app.hook_details.release_hook_details import ReleaseHookDetails
from app.mongo.registration_cursor import RegistrationCursor
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestReleaseHookDetails:
    async def test__repr(self):
        assert f"{ReleaseHookDetails('repo', '1.0', '123321', False)}" \
               == "<ReleaseHookDetails repository: repo, tag: 1.0, release_target: 123321, is_prerelease: False >"

    async def test__get_query(self):
        assert ReleaseHookDetails('repo', '1.0', '123321', True).get_query() == {'repository': 'repo'}

    async def test__get_allowed_parameters(self):
        assert ReleaseHookDetails('repo', '1.0', '123321', True).get_allowed_parameters() \
               == {'tag': '1.0', 'release_target': '123321', 'is_prerelease': True}

    async def test__get_ref(self):
        assert ReleaseHookDetails('repo', '1.0', '123321', True).get_ref() == '123321'

    async def test__setup_final_params(self):
        registration_cursor = mock(spec=RegistrationCursor, strict=True)
        ReleaseHookDetails('repo', '1.0', '123321', True).setup_final_param_values(registration_cursor)

    async def test__should_trigger(self):
        github_client = mock(spec=GithubClient, strict=True)

        registration_cursor = mock({'file_restrictions': []}, spec=RegistrationCursor, strict=True)
        assert await ReleaseHookDetails('repo', '1.0', '123321', True).should_trigger(registration_cursor, github_client)

        registration_cursor = mock({'file_restrictions': ['README.md']}, spec=RegistrationCursor, strict=True)
        expect(github_client).are_files_in_repo('repo', '123321', ['README.md']).thenReturn(async_value(False))
        assert not await ReleaseHookDetails('repo', '1.0', '123321', True).should_trigger(registration_cursor, github_client)

        registration_cursor = mock({'file_restrictions': ['README.md']}, spec=RegistrationCursor, strict=True)
        expect(github_client).are_files_in_repo('repo', '123321', ['README.md']).thenReturn(async_value(True))
        assert await ReleaseHookDetails('repo', '1.0', '123321', True).should_trigger(registration_cursor, github_client)

    async def test__get_event_type(self):
        assert ReleaseHookDetails('repo', '1.0', '123321', True).get_event_type() == EventType.RELEASE
