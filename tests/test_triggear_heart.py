import asyncio
import logging

import pytest
from mockito import mock, expect, when, captor

from app.clients.async_client import AsyncClientNotFoundException, AsyncClientException
from app.clients.github_client import GithubClient
from app.clients.jenkins_client import JenkinsClient
from app.clients.jenkinses_clients import JenkinsesClients
from app.clients.mongo_client import MongoClient
from app.hook_details.hook_details import HookDetails
from app.hook_details.hook_params_parser import HookParamsParser
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

    async def test__when_job_does_exist__it_should_be_triggered(self):
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
        when(jenkins_client).get_jobs_next_build_number('job_path').thenReturn(async_value(3))

        triggear_heart = TriggearHeart(mongo_client, github_client, jenkinses_clients)
        expect(triggear_heart).trigger_registered_job(hook_details, registration_cursor).thenReturn(async_value(None))
        # when
        await triggear_heart.trigger_registered_jobs(hook_details)

    async def test__when_job_should_not_be_triggered__warning_is_displayed(self):
        mock(logging, strict=True)
        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        jenkinses_clients: JenkinsesClients = mock(spec=JenkinsesClients, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock(
            {'jenkins_url': 'url', 'job_name': 'job_path'},
            spec=RegistrationCursor,
            strict=True
        )

        when(mongo_client).get_registered_jobs(hook_details).thenReturn(async_iter(registration_cursor))
        when(hook_details).should_trigger(registration_cursor, github_client).thenReturn(async_value(False))

        triggear_heart = TriggearHeart(mongo_client, github_client, jenkinses_clients)
        expect(triggear_heart, times=0).trigger_registered_job(hook_details, registration_cursor).thenReturn(async_value(None))
        arg_captor = captor()
        expect(logging).warning(arg_captor)
        # when
        await triggear_heart.trigger_registered_jobs(hook_details)
        assert isinstance(arg_captor.value, str)
        assert 'will not be run due to unmet registration restrictions in' in arg_captor.value

    async def test__when_job_url_is_none__not_found_status_is_not_reported(self):
        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock(
            {'jenkins_url': 'url', 'job_name': 'job_path'},
            spec=RegistrationCursor,
            strict=True
        )

        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        jenkinses_clients: JenkinsesClients = mock(spec=JenkinsesClients, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        triggear_heart = TriggearHeart(mongo_client, github_client, jenkinses_clients)

        expect(github_client, times=0).create_github_build_status(any, any, any, any, any, any)
        await triggear_heart.report_not_found_build_to_github(hook_details, registration_cursor, None, 3)

    async def test__when_job_url_is_none__unaccepted_params_status_is_not_reported(self):
        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock(
            {'jenkins_url': 'url', 'job_name': 'job_path'},
            spec=RegistrationCursor,
            strict=True
        )

        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        jenkinses_clients: JenkinsesClients = mock(spec=JenkinsesClients, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        triggear_heart = TriggearHeart(mongo_client, github_client, jenkinses_clients)

        expect(github_client, times=0).create_github_build_status(any, any, any, any, any, any)
        await triggear_heart.report_unaccepted_parameters_to_github(hook_details, registration_cursor, None, 3, {})

    async def test__when_job_url_is_not_none__not_found_status_is_reported(self):
        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock(
            {'jenkins_url': 'url', 'job_name': 'job_path', 'repo': 'repo'},
            spec=RegistrationCursor,
            strict=True
        )

        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        jenkinses_clients: JenkinsesClients = mock(spec=JenkinsesClients, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        triggear_heart = TriggearHeart(mongo_client, github_client, jenkinses_clients)

        expect(hook_details).get_ref().thenReturn('ref')
        expect(github_client).create_github_build_status(repo='repo',
                                                         sha='ref',
                                                         state="error",
                                                         url='url',
                                                         description="Triggear cant find build url:job_path #3",
                                                         context='job_path').thenReturn(async_value(None))
        await triggear_heart.report_not_found_build_to_github(hook_details, registration_cursor, 'url', 3)

    async def test__when_job_url_is_not_none__unaccepted_params_status_is_reported(self):
        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock(
            {'jenkins_url': 'url', 'job_name': 'job_path', 'repo': 'repo'},
            spec=RegistrationCursor,
            strict=True
        )

        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        jenkinses_clients: JenkinsesClients = mock(spec=JenkinsesClients, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        triggear_heart = TriggearHeart(mongo_client, github_client, jenkinses_clients)

        expect(hook_details).get_ref().thenReturn('ref')
        expect(github_client).create_github_build_status(repo='repo',
                                                         sha='ref',
                                                         state="error",
                                                         url='url',
                                                         description="Job url:job_path did not accept requested parameters None",
                                                         context='job_path').thenReturn(async_value(None))
        await triggear_heart.report_unaccepted_parameters_to_github(hook_details, registration_cursor, 'url', 3, None)

    async def test__trigger_registered_job__success_flow(self):
        mock(HookParamsParser)
        mock(asyncio)

        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock(
            {'jenkins_url': 'url', 'job_name': 'job_path', 'repo': 'repo'},
            spec=RegistrationCursor,
            strict=True
        )

        jenkins_client: JenkinsClient = mock(spec=JenkinsClient, strict=True)
        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        jenkinses_clients: JenkinsesClients = mock(spec=JenkinsesClients, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        triggear_heart = TriggearHeart(mongo_client, github_client, jenkinses_clients)

        expect(hook_details).setup_final_param_values(registration_cursor)
        expect(HookParamsParser).get_requested_parameters_values(hook_details, registration_cursor).thenReturn({})
        expect(jenkinses_clients).get_jenkins('url').thenReturn(jenkins_client)
        expect(jenkins_client).get_jobs_next_build_number('job_path').thenReturn(async_value(3))
        expect(jenkins_client).get_job_url('job_path').thenReturn(async_value('job_url'))
        expect(jenkins_client).build_jenkins_job('job_path', {}).thenReturn(async_value(None))
        expect(jenkins_client).get_build_info_data('job_path', 3)\
            .thenReturn(async_value({'url': 'job_url'}))\
            .thenReturn(async_value({'url': 'job_url', 'result': 'SUCCESS'}))
        expect(hook_details).get_ref().thenReturn('ref')
        expect(github_client).create_github_build_status(repo='repo',
                                                         sha='ref',
                                                         state='pending',
                                                         url='job_url',
                                                         description='build in progress',
                                                         context='job_path').thenReturn(async_value(None))
        expect(jenkins_client).is_job_building('job_path', 3).thenReturn(async_value(True)).thenReturn(async_value(False))
        expect(asyncio).sleep(1).thenReturn(async_value(None))
        expect(github_client).create_github_build_status(repo='repo',
                                                         sha='ref',
                                                         state='success',
                                                         url='job_url',
                                                         description='build succeeded',
                                                         context='job_path').thenReturn(async_value(None))

        await triggear_heart.trigger_registered_job(hook_details, registration_cursor)

    async def test__trigger_registered_job__when_build_job_raises__status_is_reported(self):
        mock(HookParamsParser)

        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock(
            {'jenkins_url': 'url', 'job_name': 'job_path', 'repo': 'repo'},
            spec=RegistrationCursor,
            strict=True
        )

        jenkins_client: JenkinsClient = mock(spec=JenkinsClient, strict=True)
        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        jenkinses_clients: JenkinsesClients = mock(spec=JenkinsesClients, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        triggear_heart = TriggearHeart(mongo_client, github_client, jenkinses_clients)

        expect(hook_details).setup_final_param_values(registration_cursor)
        expect(HookParamsParser).get_requested_parameters_values(hook_details, registration_cursor).thenReturn({})
        expect(jenkinses_clients).get_jenkins('url').thenReturn(jenkins_client)
        expect(jenkins_client).get_jobs_next_build_number('job_path').thenReturn(async_value(3))
        expect(jenkins_client).get_job_url('job_path').thenReturn(async_value('job_url'))
        expect(jenkins_client).build_jenkins_job('job_path', {}).thenRaise(AsyncClientException('terrible', 500))
        expect(triggear_heart).report_unaccepted_parameters_to_github(hook_details, registration_cursor, 'job_url', 3, {})\
            .thenReturn(async_value(None))

        await triggear_heart.trigger_registered_job(hook_details, registration_cursor)

    async def test__trigger_registered_job__when_build_info_is_none__status_is_reported(self):
        mock(HookParamsParser)
        mock(asyncio)

        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock(
            {'jenkins_url': 'url', 'job_name': 'job_path', 'repo': 'repo'},
            spec=RegistrationCursor,
            strict=True
        )

        jenkins_client: JenkinsClient = mock(spec=JenkinsClient, strict=True)
        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        jenkinses_clients: JenkinsesClients = mock(spec=JenkinsesClients, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        triggear_heart = TriggearHeart(mongo_client, github_client, jenkinses_clients)

        expect(hook_details).setup_final_param_values(registration_cursor)
        expect(HookParamsParser).get_requested_parameters_values(hook_details, registration_cursor).thenReturn({})
        expect(jenkinses_clients).get_jenkins('url').thenReturn(jenkins_client)
        expect(jenkins_client).get_jobs_next_build_number('job_path').thenReturn(async_value(3))
        expect(jenkins_client).get_job_url('job_path').thenReturn(async_value('job_url'))
        expect(jenkins_client).build_jenkins_job('job_path', {}).thenReturn(async_value(None))
        expect(jenkins_client).get_build_info_data('job_path', 3)\
            .thenReturn(async_value(None))
        expect(hook_details).get_ref().thenReturn('ref')
        expect(github_client).create_github_build_status(repo='repo',
                                                         sha='ref',
                                                         state='error',
                                                         url='job_url',
                                                         description='Triggear cant find build url:job_path #3',
                                                         context='job_path').thenReturn(async_value(None))

        await triggear_heart.trigger_registered_job(hook_details, registration_cursor)

    async def test__trigger_registered_job__second_build_info_is_none(self):
        mock(HookParamsParser)
        mock(asyncio)

        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock(
            {'jenkins_url': 'url', 'job_name': 'job_path', 'repo': 'repo'},
            spec=RegistrationCursor,
            strict=True
        )

        jenkins_client: JenkinsClient = mock(spec=JenkinsClient, strict=True)
        mongo_client: MongoClient = mock(spec=MongoClient, strict=True)
        jenkinses_clients: JenkinsesClients = mock(spec=JenkinsesClients, strict=True)
        github_client: GithubClient = mock(spec=GithubClient, strict=True)
        triggear_heart = TriggearHeart(mongo_client, github_client, jenkinses_clients)

        expect(hook_details).setup_final_param_values(registration_cursor)
        expect(HookParamsParser).get_requested_parameters_values(hook_details, registration_cursor).thenReturn({})
        expect(jenkinses_clients).get_jenkins('url').thenReturn(jenkins_client)
        expect(jenkins_client).get_jobs_next_build_number('job_path').thenReturn(async_value(3))
        expect(jenkins_client).get_job_url('job_path').thenReturn(async_value('job_url'))
        expect(jenkins_client).build_jenkins_job('job_path', {}).thenReturn(async_value(None))
        expect(jenkins_client).get_build_info_data('job_path', 3)\
            .thenReturn(async_value({'url': 'job_url'}))\
            .thenReturn(async_value(None))
        expect(hook_details).get_ref().thenReturn('ref')
        expect(github_client).create_github_build_status(repo='repo',
                                                         sha='ref',
                                                         state='pending',
                                                         url='job_url',
                                                         description='build in progress',
                                                         context='job_path').thenReturn(async_value(None))
        expect(jenkins_client).is_job_building('job_path', 3).thenReturn(async_value(True)).thenReturn(async_value(False))
        expect(asyncio).sleep(1).thenReturn(async_value(None))

        await triggear_heart.trigger_registered_job(hook_details, registration_cursor)
