import asyncio

import pytest
import time

from mockito import mock, when, expect, captor

from app.clients.async_client import AsyncClientException, AsyncClient, Payload
from app.clients.jenkins_client import JenkinsClient, JenkinsInstanceConfig
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestJenkinsClient:
    @pytest.mark.parametrize("job_info, expected_url", [
        ({'url': 'http://example.com'}, 'http://example.com'),
        ({}, None),
    ])
    async def test__get_job_url__properly_calls_jenkins_client(self, job_info, expected_url):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        tested_client = JenkinsClient(instance_config)
        expect(tested_client).get_job_info('job').thenReturn(async_value(job_info))

        assert expected_url == await tested_client.get_job_url('job')

    async def test__is_job_building__returns_none__when_build_info_is_none(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')
        tested_client = JenkinsClient(instance_config)
        expect(tested_client).get_build_info_data('job', 12).thenReturn(async_value(None))

        assert await tested_client.is_job_building('job', 12) is None

    async def test__is_job_building__returns_none__when_jenkins_returns_504(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')
        tested_client = JenkinsClient(instance_config)
        expect(tested_client).get_build_info_data('job', 12).thenRaise(AsyncClientException('Timeout', 504))

        assert await tested_client.is_job_building('job', 12) is None

    async def test__is_job_building__raises__when_client_status_is_different_then_504(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')
        tested_client = JenkinsClient(instance_config)
        expect(tested_client).get_build_info_data('job', 12).thenRaise(AsyncClientException('Timeout', 404))

        with pytest.raises(AsyncClientException):
            await tested_client.is_job_building('job', 12)

    async def test__get_build_info__returns_none__in_case_of_timeout(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        mock(time)
        mock(asyncio)

        when(time).monotonic() \
            .thenReturn(0) \
            .thenReturn(15) \
            .thenReturn(31)
        when(asyncio).sleep(1).thenReturn(async_value(None))

        tested_client = JenkinsClient(instance_config)
        expect(tested_client).get_build_info(job_path='job', build_number=23).thenRaise(AsyncClientException('job not found', 404))

        assert await tested_client.get_build_info_data('job', 23) is None

    async def test__get_build_info__raises__in_case_non_404_errors(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        mock(time)

        when(time).monotonic() \
            .thenReturn(0) \
            .thenReturn(15) \
            .thenReturn(31)

        tested_client = JenkinsClient(instance_config)
        expect(tested_client).get_build_info(job_path='job', build_number=23).thenRaise(AsyncClientException('something went wrong', 500))

        with pytest.raises(AsyncClientException) as exception:
            await tested_client.get_build_info_data('job', 23)
        assert exception.value.status == 500
        assert exception.value.message == 'something went wrong'

    async def test__get_build_info__returns_build_info__in_case_of_no_timeout(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        mock(time)
        mock(asyncio)

        when(time).monotonic()\
            .thenReturn(0)\
            .thenReturn(15)
        tested_client = JenkinsClient(instance_config)
        expect(tested_client).get_build_info(job_path='job', build_number=23).thenReturn(async_value({'some': 'values'}))

        assert {'some': 'values'} == await tested_client.get_build_info_data('job', 23)

    async def test__is_job_building__returns_status__when_build_info_is_valid(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        tested_client = JenkinsClient(instance_config)
        expect(tested_client).get_build_info_data('job', 12).thenReturn(async_value({'building': True}))

        assert await tested_client.is_job_building('job', 12)

    async def test__build_jenkins_job__calls_jenkins_properly(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        tested_client = JenkinsClient(instance_config)
        expect(tested_client)._build_jenkins_job('job', parameters={'param': 'value'}).thenReturn(async_value(None))

        await tested_client.build_jenkins_job('job', {'param': 'value'})

    async def test__when_build_jenkins_job_raises_400_nothing_is_submitted__should_be_recalled_with_empty_param(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        tested_client = JenkinsClient(instance_config)
        expect(tested_client, times=1)._build_jenkins_job('job', parameters=None).thenRaise(AsyncClientException('Nothing is submitted', 400))
        expect(tested_client, times=1)._build_jenkins_job('job', parameters={'': ''}).thenReturn(async_value(None))

        await tested_client.build_jenkins_job('job', None)

    async def test__when_build_jenkins_job_raises_random_http_error__should_be_thrown(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        tested_client = JenkinsClient(instance_config)
        expect(tested_client, times=1)._build_jenkins_job('job', parameters=None).thenRaise(AsyncClientException('Something went bad', 401))
        expect(tested_client, times=0)._build_jenkins_job('job', parameters={'': ''})

        with pytest.raises(AsyncClientException) as error:
            await tested_client.build_jenkins_job('job', None)
        assert error.value.status == 401
        assert error.value.message == 'Something went bad'

    async def test__when_get_async_client_is_called__async_client_is_created_once__and_returned_in_all_successive_calls(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        tested_client = JenkinsClient(instance_config)
        async_client: AsyncClient = tested_client.get_async_jenkins()
        assert async_client.base_url == 'url'
        assert async_client.session_headers == {
            'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
            'Content-Type': 'application/json'
        }
        assert tested_client.get_async_jenkins() == async_client

    async def test__get_job_folder_and_name__should_return_properly_formatted_route_to_folder_and_job_name(self):
        folder, job_name = JenkinsClient.get_job_folder_and_name('triggear/tests/run')
        assert 'job/triggear/job/tests/' == folder
        assert 'run' == job_name

    async def test__get_job_info__calls_proper_jenkins_endpoint(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')
        jenkins_client = JenkinsClient(instance_config)

        async_client: AsyncClient = mock(spec=AsyncClient, strict=True)

        expect(jenkins_client).get_async_jenkins().thenReturn(async_client)
        expect(async_client).get(route='job/triggear/job/tests/api/json?depth=0').thenReturn(async_value({}))

        assert {} == await jenkins_client.get_job_info('triggear/tests')

    async def test__get_jobs_next_build_number__parses_job_info_properly(self):
        jenkins_client = JenkinsClient(mock())

        expect(jenkins_client).get_job_info('triggear/tests').thenReturn(async_value({'nextBuildNumber': 231}))

        assert 231 == await jenkins_client.get_jobs_next_build_number('triggear/tests')

    async def test__get_build_info__calls_proper_jenkins_endpoint(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')
        jenkins_client = JenkinsClient(instance_config)

        async_client: AsyncClient = mock(spec=AsyncClient, strict=True)

        expect(jenkins_client).get_async_jenkins().thenReturn(async_client)
        expect(async_client).get(route='job/triggear/job/tests/213/api/json?depth=0').thenReturn(async_value({}))

        assert {} == await jenkins_client.get_build_info('triggear/tests', 213)

    async def test__set_crumb__calls_proper_jenkins_endpoint__and_result_is_available_via_get(self):
        jenkins_client = JenkinsClient(mock())

        async_client: AsyncClient = mock(spec=AsyncClient, strict=True)

        expect(jenkins_client).get_async_jenkins().thenReturn(async_client)
        expect(async_client).get(route='crumbIssuer/api/json')\
            .thenReturn(async_value({'crumbRequestField': 'Jenkins-Crumb', 'crumb': '123321456654'}))

        await jenkins_client.set_crumb_header()
        assert {'Jenkins-Crumb': '123321456654'} == await jenkins_client.get_crumb_header()

    async def test__prior_to_crumb_set__get_crumb_should_return_none(self):
        jenkins_client = JenkinsClient(mock())
        assert await jenkins_client.get_crumb_header() is None

    async def test__inner_build_jenkins_job__calls_proper_jenkins_endpoint(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')
        jenkins_client = JenkinsClient(instance_config)

        async_client: AsyncClient = mock(spec=AsyncClient, strict=True)

        expect(jenkins_client).get_async_jenkins().thenReturn(async_client)
        arg_captor = captor()
        expect(async_client)\
            .post(route='job/triggear/job/tests/buildWithParameters', params=arg_captor, headers=None, content_type='text/plain')\
            .thenReturn(async_value({}))

        assert {} == await jenkins_client._build_jenkins_job('triggear/tests', {'param': 'value'})
        params: Payload = arg_captor.value
        assert params.data.get('param') == 'value'

    async def test__when_build_jenkins_job_raises_403_no_valid_crumb__should_be_recalled_with_crumb_header(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        tested_client = JenkinsClient(instance_config)
        expect(tested_client, times=2)._build_jenkins_job('job', parameters={'param': 'value'})\
            .thenRaise(AsyncClientException('No valid crumb was included in the request', 403))\
            .thenReturn(async_value(None))
        expect(tested_client, times=1).set_crumb_header().thenReturn(async_value(None))

        await tested_client.build_jenkins_job('job', {'param': 'value'})
