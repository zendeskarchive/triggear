import asyncio

import jenkins
import pytest
import time
from urllib.error import HTTPError
from mockito import mock, when, expect

from app.clients.jenkins_client import JenkinsClient
from app.config.triggear_config import JenkinsInstanceConfig
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestJenkinsClient:
    @pytest.mark.parametrize("job_info, expected_url", [
        ({'url': 'http://example.com'}, 'http://example.com'),
        ({}, None),
    ])
    async def test__get_job_url__properly_calls_jenkins_client(self, job_info, expected_url):
        jenkins_client = mock()
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        when(jenkins)\
            .Jenkins(url='url', username='username', password='password')\
            .thenReturn(jenkins_client)
        expect(jenkins_client).get_job_info('job').thenReturn(job_info)

        tested_client = JenkinsClient(instance_config)

        assert expected_url == await tested_client.get_job_url('job')

    async def test__is_job_building__returns_none__when_build_info_is_none(self):
        jenkins_client = mock()
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        when(jenkins)\
            .Jenkins(url='url', username='username', password='password')\
            .thenReturn(jenkins_client)
        expect(jenkins_client).get_build_info('job', 12).thenReturn(None)

        tested_client = JenkinsClient(instance_config)

        assert await tested_client.is_job_building('job', 12) is None

    async def test__get_build_info__returns_none__in_case_of_timeout(self):
        jenkins_client = mock()
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        when(jenkins)\
            .Jenkins(url='url', username='username', password='password')\
            .thenReturn(jenkins_client)
        mock(time)
        mock(asyncio)

        when(time).monotonic() \
            .thenReturn(0) \
            .thenReturn(15) \
            .thenReturn(31)
        when(asyncio).sleep(1).thenReturn(async_value(None))
        expect(jenkins_client).get_build_info('job', 23).thenRaise(jenkins.NotFoundException())

        tested_client = JenkinsClient(instance_config)

        assert await tested_client.get_build_info('job', 23) is None

    async def test__get_build_info__returns_build_info__in_case_of_no_timeout(self):
        jenkins_client = mock()
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        when(jenkins)\
            .Jenkins(url='url', username='username', password='password')\
            .thenReturn(jenkins_client)
        mock(time)
        mock(asyncio)

        when(time).monotonic()\
            .thenReturn(0)\
            .thenReturn(15)
        expect(jenkins_client).get_build_info('job', 23).thenReturn({'some': 'values'})

        assert {'some': 'values'} == await JenkinsClient(instance_config).get_build_info('job', 23)

    async def test__is_job_building__returns_status__when_build_info_is_valid(self):
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        tested_client = JenkinsClient(instance_config)
        expect(tested_client).get_build_info('job', 12).thenReturn(async_value({'building': True}))

        assert await tested_client.is_job_building('job', 12)

    async def test__build_jenkins_job__calls_jenkins_properly(self):
        jenkins_client = mock()
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        when(jenkins)\
            .Jenkins(url='url', username='username', password='password')\
            .thenReturn(jenkins_client)

        expect(jenkins_client).build_job('job', parameters={'param': 'value'})

        JenkinsClient(instance_config).build_jenkins_job('job', {'param': 'value'})

    async def test__when_build_jenkins_job_raises_400_nothing_is_submitted__should_be_recalled_with_empty_param(self):
        jenkins_client = mock()
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        when(jenkins)\
            .Jenkins(url='url', username='username', password='password')\
            .thenReturn(jenkins_client)

        when(jenkins_client).build_job('job', parameters=None).thenRaise(HTTPError(None, 400, 'Nothing is submitted', None, None))
        expect(jenkins_client, times=1).build_job('job', parameters={'': ''})

        JenkinsClient(instance_config).build_jenkins_job('job', None)

    async def test__when_build_jenkins_job_raises_random_http_error__should_be_thrown(self):
        jenkins_client = mock()
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        when(jenkins)\
            .Jenkins(url='url', username='username', password='password')\
            .thenReturn(jenkins_client)

        when(jenkins_client).build_job('job', parameters=None).thenRaise(HTTPError(None, 401, 'Something went bad', None, None))
        expect(jenkins_client, times=0).build_job('job', parameters={'': ''})

        with pytest.raises(HTTPError) as error:
            JenkinsClient(instance_config).build_jenkins_job('job', None)
        assert error.value.code == 401
        assert error.value.msg == 'Something went bad'

    @pytest.mark.parametrize("job_info, expected_url", [
        ({'url': 'http://example.com'}, 'http://example.com'),
        ({}, None),
    ])
    async def test__get_job_url__properly_calls_jenkins_client(self, job_info, expected_url):
        jenkins_client = mock()
        instance_config = JenkinsInstanceConfig('url', 'username', 'password')

        when(jenkins)\
            .Jenkins(url='url', username='username', password='password')\
            .thenReturn(jenkins_client)

        expect(jenkins_client).get_job_info('job').thenReturn(job_info)

        assert expected_url == await JenkinsClient(instance_config).get_job_url('job')
