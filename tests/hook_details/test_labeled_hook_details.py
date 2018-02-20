import pytest
from mockito import mock, expect

from app.clients.github_client import GithubClient
from app.enums.event_types import EventType
from app.hook_details.labeled_hook_details import LabeledHookDetails
from app.mongo.registration_cursor import RegistrationCursor
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestLabeledHookDetails:
    async def test__repr(self):
        assert f"{LabeledHookDetails('repo', 'master', '123321', 'custom', 'karolgil', 'https://pr.url')}" \
               == "<LabeledHookDetails repository: repo, branch: master, sha: 123321, label: custom, who: karolgil, pr_url: https://pr.url>"

    async def test__get_query(self):
        assert LabeledHookDetails('repo', 'master', '123321', 'custom', 'karolgil', 'https://pr.url').get_query() \
               == {'repository': 'repo', 'labels': 'custom'}

    async def test__get_allowed_parameters(self):
        assert LabeledHookDetails('repo', 'master', '123321', 'custom', 'karolgil', 'https://pr.url').get_allowed_parameters() \
               == {'branch': 'master', 'sha': '123321', 'who': 'karolgil', 'pr_url': 'https://pr.url'}

    async def test__get_ref(self):
        assert LabeledHookDetails('repo', 'master', '123321', 'custom', 'karolgil', 'https://pr.url').get_ref() == '123321'

    async def test__setup_final_params(self):
        registration_cursor = mock(spec=RegistrationCursor, strict=True)
        LabeledHookDetails('repo', 'master', '123321', 'custom', 'karolgil', 'https://pr.url').setup_final_param_values(registration_cursor)

    async def test__should_trigger(self):
        github_client = mock(spec=GithubClient, strict=True)

        registration_cursor = mock({'file_restrictions': []}, spec=RegistrationCursor, strict=True)
        assert await LabeledHookDetails('repo', 'master', '123321', 'custom', 'karolgil', 'https://pr.url')\
            .should_trigger(registration_cursor, github_client)

        registration_cursor = mock({'file_restrictions': ['README.md']}, spec=RegistrationCursor, strict=True)
        expect(github_client).are_files_in_repo('repo', '123321', ['README.md']).thenReturn(async_value(False))
        assert not await LabeledHookDetails('repo', 'master', '123321', 'custom', 'karolgil', 'https://pr.url')\
            .should_trigger(registration_cursor, github_client)

        registration_cursor = mock({'file_restrictions': ['README.md']}, spec=RegistrationCursor, strict=True)
        expect(github_client).are_files_in_repo('repo', '123321', ['README.md']).thenReturn(async_value(True))
        assert await LabeledHookDetails('repo', 'master', '123321', 'custom', 'karolgil', 'https://pr.url')\
            .should_trigger(registration_cursor, github_client)

    async def test__get_event_type(self):
        assert LabeledHookDetails('repo', 'master', '123321', 'custom', 'karolgil', 'https://pr.url').get_event_type() == EventType.PR_LABELED
