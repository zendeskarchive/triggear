import os
import pytest
from mockito import mock, when

from app.clients.jenkins_client import JenkinsClient
from app.clients.jenkinses_clients import JenkinsesClients
from app.config.triggear_config import TriggearConfig
from app.exceptions.triggear_error import TriggearError

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestJenkinsesClients:
    async def test__when_jenkins_for_url_is_not_in_config__should_raise(self):
        triggear_config: TriggearConfig = mock({'jenkins_instances': {}}, spec=TriggearConfig, strict=True)
        when(os).getenv('CREDS_PATH', 'creds.yml').thenReturn('./tests/config/example_configs/creds.yaml')
        jenkinses_clients = JenkinsesClients(triggear_config)

        with pytest.raises(TriggearError):
            jenkinses_clients.get_jenkins('url')

    async def test__when_jenkins_for_url_is_in_new_config__should_return_it(self):
        triggear_config: TriggearConfig = mock({'jenkins_instances': {}}, spec=TriggearConfig, strict=True)
        when(os).getenv('CREDS_PATH', 'creds.yml').thenReturn('./tests/config/example_configs/creds.yaml')
        jenkinses_clients = JenkinsesClients(triggear_config)

        jenkins_client: JenkinsClient = jenkinses_clients.get_jenkins('https://ci.triggear.com/')
        assert jenkins_client.config.url == 'https://ci.triggear.com/'
        assert jenkins_client.config.token == "other_api_token"
        assert jenkins_client.config.username == "other_user"
