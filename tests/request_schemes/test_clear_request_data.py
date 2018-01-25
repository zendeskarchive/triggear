import pytest

from app.request_schemes.clear_request_data import ClearRequestData

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestClearRequestData:
    @pytest.mark.parametrize("data", [
        {'eventType': ''},
        {'jobName': '', 'caller': ''},
        {'jobName': '', 'jenkins_url': ''}
    ])
    async def test__when_data_does_not_have_mandatory_keys__should_not_be_valid(self, data):
        assert not ClearRequestData.is_valid_clear_request_data(data)

    async def test__when_data_has_mandatory_keys__should_be_valid(self):
        data = {'eventType': '', 'jobName': '', 'jenkins_url': ''}
        assert ClearRequestData.is_valid_clear_request_data(data)
