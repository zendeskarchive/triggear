import pytest

from app.mongo.registration_query import RegistrationQuery

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestRegistrationQuery:
    async def test__registration_query(self):
        data = {
            'jenkins_url': 'url',
            'jobName': 'job',
            'labels': ['labels'],
            'branch_restrictions': ['br'],
            'eventType': 'type',
            'repository': 'repo',
            'requested_params': ['rp'],
            'file_restrictions': ['fr'],
            'change_restrictions': ['cr']
        }
        registration_query: RegistrationQuery = RegistrationQuery.from_registration_request_data(data)
        assert registration_query.file_restrictions == ['fr']
        assert registration_query.jenkins_url == 'url'
        assert registration_query.job_name == 'job'
        assert registration_query.labels == ['labels']
        assert registration_query.event_type == 'type'
        assert registration_query.change_restrictions == ['cr']
        assert registration_query.repository == 'repo'
        assert registration_query.branch_restrictions == ['br']
        assert registration_query.requested_params == ['rp']

        assert registration_query.get_registration_query() == {
            'jenkins_url': 'url',
            'repository': 'repo',
            'job': 'job'
        }

        assert registration_query.get_full_document() == {
            'jenkins_url': 'url',
            'job': 'job',
            'labels': ['labels'],
            'branch_restrictions': ['br'],
            'repository': 'repo',
            'requested_params': ['rp'],
            'file_restrictions': ['fr'],
            'change_restrictions': ['cr']
        }
