import pytest
from mockito import mock, expect, when

from app.clients.async_client import AsyncClientNotFoundException
from app.clients.github_client import GithubClient
from app.clients.jenkins_client import JenkinsClient
from app.clients.jenkinses_clients import JenkinsesClients
from app.clients.mongo_client import MongoClient
from app.hook_details.hook_details import HookDetails
from app.mongo.registration_cursor import RegistrationCursor
from app.triggear_heart import TriggearHeart
from tests.async_mockito import async_iter, async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestTriggearHeart:
    async def test__when_job_does_not_exist__it_should_have_missed_times_field_incremented(self):
        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        jenkinses_clients: JenkinsesClients = mock(spec=JenkinsesClients, strict=True)
        jenkins_client: JenkinsClient = mock(spec=JenkinsClient, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock(
            {'jenkins_url': 'url', 'job_name': 'job_path'},
            spec=RegistrationCursor,
            strict=True
        )

        when(mongo_client).get_registered_jobs(hook_details).thenReturn(async_iter(registration_cursor))
        when(hook_details).should_trigger(registration_cursor, github_client).thenReturn(async_value(True))
        when(jenkinses_clients).get_jenkins('url').thenReturn(jenkins_client)
        when(jenkins_client).get_jobs_next_build_number('job_path').thenRaise(AsyncClientNotFoundException('Job not found'))

        expect(hook_details).get_query()
        expect(mongo_client, strict=True, times=1).increment_missed_counter(hook_details, registration_cursor).thenReturn(async_value(None))

        # when
        await TriggearHeart(mongo_client, github_client, jenkinses_clients).trigger_registered_jobs(hook_details)
