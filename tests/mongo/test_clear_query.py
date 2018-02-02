import pytest

from app.mongo.clear_query import ClearQuery

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestClearQuery:
    async def test__builder_method(self):
        data = {'jenkins_url': 'url', 'jobName': 'job', 'eventType': 'type'}
        result = ClearQuery.from_clear_request_data(data)
        assert result.event_type == 'type'
        assert result.jenkins_url == 'url'
        assert result.job_name == 'job'

    async def test__get_query(self):
        data = {'jenkins_url': 'url', 'jobName': 'job', 'eventType': 'type'}
        assert  ClearQuery.from_clear_request_data(data).get_clear_query() == {'job': 'job', 'jenkins_url': 'url'}
