from typing import Dict

import pytest

from app.request_schemes.deployment_status_request_data import DeploymentStatusRequestData

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestDeploymentStatusRequestData:
    @pytest.mark.parametrize("data", [
        {'ref': ''},
        {'repo': '', 'ref': ''},
        {'repo': '', 'ref': '', 'environment': ''},
        {'repo': '', 'ref': '', 'description': '', 'environment': ''},
        {'repo': '', 'ref': '', 'description': '', 'state': '', 'targetUrl': ''},
        {'repo': '', 'ref': '', 'description': '', 'state': '', 'environment': '', 'targetUrl': ''},
        {'repo': '', 'ref': '', 'description': '', 'state': 'invalid', 'environment': '', 'targetUrl': ''}
    ])
    async def test__when_data_does_not_have_mandatory_keys__should_not_be_valid(self, data):
        assert not DeploymentStatusRequestData.is_valid_deployment_status_request_data(data)

    @pytest.mark.parametrize("data", [
        {'repo': '', 'ref': '', 'description': '', 'environment': '', 'state': 'pending', 'targetUrl': ''},
        {'repo': '', 'ref': '', 'description': '', 'environment': '', 'state': 'success', 'targetUrl': ''},
        {'repo': '', 'ref': '', 'description': '', 'environment': '', 'state': 'error', 'targetUrl': ''},
        {'repo': '', 'ref': '', 'description': '', 'environment': '', 'state': 'failure', 'targetUrl': ''}
    ])
    async def test__when_data_has_mandatory_keys__should_be_valid(self, data: Dict):
        assert DeploymentStatusRequestData.is_valid_deployment_status_request_data(data)
