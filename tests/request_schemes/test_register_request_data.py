import pytest

from app.request_schemes.register_request_data import RegisterRequestData

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestRegisterRequestData:
    @pytest.mark.parametrize("data", [
        {'eventType': ''},
        {'eventType': '', 'repository': ''},
        {'eventType': '', 'repository': '', 'jobName': ''},
        {'eventType': '', 'repository': '', 'jobName': '', 'labels': ''}
    ])
    async def test__when_data_does_not_have_mandatory_keys__should_not_be_valid(self, data):
        assert not RegisterRequestData.is_valid_register_request_data(data)

    async def test__when_data_has_mandatory_keys__and_no_requested_params__should_be_valid(self):
        data = {'eventType': '', 'repository': '', 'jobName': '', 'labels': [], 'requested_params': []}
        assert RegisterRequestData.is_valid_register_request_data(data)

    async def test__when_data_has_mandatory_keys__and_valid_requested_params__should_be_valid(self):
        data = {'eventType': '', 'repository': '', 'jobName': '', 'labels': [], 'requested_params': ['branch', 'sha', 'tag']}
        assert RegisterRequestData.is_valid_register_request_data(data)

    async def test__when_data_has_mandatory_keys__but_invalid_requested_params__should_not_be_valid(self):
        data = {'eventType': '', 'repository': '', 'jobName': '', 'labels': [], 'requested_params': ['branch', 'SHA', 'TAG']}
        assert not RegisterRequestData.is_valid_register_request_data(data)
