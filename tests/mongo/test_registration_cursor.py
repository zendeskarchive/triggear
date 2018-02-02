import pytest
from mockito import mock, expect
from motor.motor_asyncio import AsyncIOMotorCursor

from app.mongo.registration_cursor import RegistrationCursor

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestRegistrationCursor:
    async def test__get_job_name(self):
        cursor: AsyncIOMotorCursor = mock(spec=AsyncIOMotorCursor, strict=True)
        expect(cursor).__getitem__('job').thenReturn('job')
        assert RegistrationCursor(cursor).job_name == 'job'

    async def test__get_repo(self):
        cursor: AsyncIOMotorCursor = mock(spec=AsyncIOMotorCursor, strict=True)
        expect(cursor).__getitem__('repository').thenReturn('repo')
        assert RegistrationCursor(cursor).repo == 'repo'

    async def test__get_jenkins_url(self):
        cursor: AsyncIOMotorCursor = mock(spec=AsyncIOMotorCursor, strict=True)
        expect(cursor).__getitem__('jenkins_url').thenReturn('url')
        assert RegistrationCursor(cursor).jenkins_url == 'url'

    async def test__get_labels(self):
        cursor: AsyncIOMotorCursor = mock(spec=AsyncIOMotorCursor, strict=True)
        expect(cursor).get('labels').thenReturn(['custom'])
        assert RegistrationCursor(cursor).labels == ['custom']

    async def test__get_requested_params(self):
        cursor: AsyncIOMotorCursor = mock(spec=AsyncIOMotorCursor, strict=True)
        expect(cursor).get('requested_params').thenReturn(['sha', 'branch'])
        assert RegistrationCursor(cursor).requested_params == ['sha', 'branch']

    async def test__get_change_restrictions(self):
        cursor: AsyncIOMotorCursor = mock(spec=AsyncIOMotorCursor, strict=True)
        expect(cursor).get('change_restrictions').thenReturn(['.git', '.gitignore'])
        assert RegistrationCursor(cursor).change_restrictions == ['.git', '.gitignore']

    async def test__get_branch_restrictions(self):
        cursor: AsyncIOMotorCursor = mock(spec=AsyncIOMotorCursor, strict=True)
        expect(cursor).get('branch_restrictions').thenReturn(['master'])
        assert RegistrationCursor(cursor).branch_restrictions == ['master']

    async def test__get_file_restrictions(self):
        cursor: AsyncIOMotorCursor = mock(spec=AsyncIOMotorCursor, strict=True)
        expect(cursor).get('file_restrictions').thenReturn(['README.md', '.gitignore'])
        assert RegistrationCursor(cursor).file_restrictions == ['README.md', '.gitignore']

    async def test__repr(self):
        cursor: AsyncIOMotorCursor = mock(spec=AsyncIOMotorCursor, strict=True)
        expect(cursor).__getitem__('job').thenReturn('job')
        expect(cursor).__getitem__('repository').thenReturn('repo')
        expect(cursor).__getitem__('jenkins_url').thenReturn('url')
        expect(cursor).get('labels').thenReturn(['custom'])
        expect(cursor).get('requested_params').thenReturn(['sha', 'branch'])
        expect(cursor).get('change_restrictions').thenReturn(['.git', '.gitignore'])
        expect(cursor).get('branch_restrictions').thenReturn(['master'])
        expect(cursor).get('file_restrictions').thenReturn(['README.md', '.gitignore'])
        assert f"{RegistrationCursor(cursor)}" == "<RegistrationCursor " \
                                                  "job_name: job, " \
                                                  "repo: repo, " \
                                                  "jenkins_url: url, " \
                                                  "labels: ['custom'], " \
                                                  "requested_params: ['sha', 'branch'], " \
                                                  "change_restrictions: ['.git', '.gitignore'], " \
                                                  "branch_restrictions: ['master'], " \
                                                  "file_restrictions: ['README.md', '.gitignore'] >"
