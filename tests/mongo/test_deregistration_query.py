import pytest

from app.mongo.deregistration_query import DeregistrationQuery

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestDeregistrationQuery:
    async def test__builder_method(self):
        data = {'jenkins_url': 'url', 'jobName': 'job', 'eventType': 'type', 'caller': 'pythonista'}
        result = DeregistrationQuery.from_deregistration_request_data(data)
        assert result.event_type == 'type'
        assert result.jenkins_url == 'url'
        assert result.job_name == 'job'
        assert result.caller == 'pythonista'

    async def test__get_query(self):
        data = {'jenkins_url': 'url', 'jobName': 'job', 'eventType': 'type', 'caller': 'pythonista'}
        assert DeregistrationQuery.from_deregistration_request_data(data).get_deregistration_query() == {'job': 'job', 'jenkins_url': 'url'}
