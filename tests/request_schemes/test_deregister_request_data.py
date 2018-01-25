import pytest

from app.request_schemes.deregister_request_data import DeregisterRequestData

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestDeregisterRequestData:
    @pytest.mark.parametrize("data", [
        {'eventType': ''},
        {'eventType': '', 'jobName': ''},
        {'eventType': '', 'jobName': ''},
        {'eventType': '', 'caller': ''},
        {'jobName': '', 'caller': ''},
        {'jobName': '', 'jenkins_url': '', 'caller': ''}
    ])
    async def test__when_data_does_not_have_mandatory_keys__should_not_be_valid(self, data):
        assert not DeregisterRequestData.is_valid_deregister_request_data(data)

    async def test__when_data_has_mandatory_keys__should_be_valid(self):
        data = {'eventType': '', 'repository': '', 'jobName': '', 'caller': '', 'jenkins_url': ''}
        assert DeregisterRequestData.is_valid_deregister_request_data(data)
