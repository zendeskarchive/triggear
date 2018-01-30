import pytest

from app.request_schemes.deployment_request_data import DeploymentRequestData

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestDeploymentRequestData:
    @pytest.mark.parametrize("data", [
        {'ref': ''},
        {'repo': '', 'ref': ''},
        {'repo': '', 'ref': '', 'environment': ''},
        {'repo': '', 'ref': '', 'description': ''}
    ])
    async def test__when_data_does_not_have_mandatory_keys__should_not_be_valid(self, data):
        assert not DeploymentRequestData.is_valid_deployment_request_data(data)

    async def test__when_data_has_mandatory_keys__should_be_valid(self):
        data = {'repo': '', 'ref': '', 'description': '', 'environment': ''}
        assert DeploymentRequestData.is_valid_deployment_request_data(data)
