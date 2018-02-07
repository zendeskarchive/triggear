import os
from typing import Dict

import pytest
import yaml
from mockito import when

from app.config.triggear_config import TriggearConfig
from app.clients.jenkins_client import JenkinsInstanceConfig

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestTriggearConfig:
    VALID_CREDS_DATA = {
        'jenkins_instances': [{
            'url': 'URL',
            'user': 'USER',
            'token': 'JENKINS_TOKEN',
        }],
        'github_token': 'GITHUB_TOKEN',
        'triggear_token': 'TRIGGEAR_TOKEN'
    }

    async def test__when_creds_path_is_invalid__should_raise_file_not_found_error(self):
        when(os).getenv('CREDS_PATH', 'creds.yml').thenReturn('does/not/exist')

        with pytest.raises(FileNotFoundError) as file_not_found_error:
            TriggearConfig().read_credentials_file()
        assert str(file_not_found_error.value) == "[Errno 2] No such file or directory: 'does/not/exist'"

    @pytest.mark.parametrize("yaml_data, missing_key", [
        ({}, 'jenkins_instances'),
        ({'jenkins_instances': []}, 'github_token'),
        ({'jenkins_instances': [], 'github_token': ''}, 'triggear_token')
    ])
    async def test__when_any_key_is_missing_in_creds_file__should_raise_proper_key_error(self, yaml_data: Dict, missing_key: str):
        when(os).getenv('CREDS_PATH', 'creds.yml').thenReturn('./tests/config/example_configs/creds.yaml')
        when(yaml).load(any).thenReturn(yaml_data)

        with pytest.raises(KeyError) as key_error:
            TriggearConfig().read_credentials_file()
        assert str(key_error.value) == f"'{missing_key}'"

    async def test__when_yaml_files_are_valid__should_store_proper_values(self):
        when(os).getenv('CREDS_PATH', 'creds.yml').thenReturn('./tests/config/example_configs/creds.yaml')

        triggear_config = TriggearConfig()

        assert triggear_config.triggear_token == 'TRIGGEAR_TOKEN'
        assert triggear_config.github_token == 'GITHUB_TOKEN'

        first_instance_url = "https://JENKINS_URL/"
        second_instance_url = "https://ci.triggear.com/"
        assert set(triggear_config.jenkins_instances.keys()) == {first_instance_url, second_instance_url}

        first_instance: JenkinsInstanceConfig = triggear_config.jenkins_instances.get(first_instance_url)
        second_instance: JenkinsInstanceConfig = triggear_config.jenkins_instances.get(second_instance_url)
        assert first_instance.url == first_instance_url
        assert first_instance.username == 'JENKINS_USER'
        assert first_instance.token == 'JENKINS_USER_API_TOKEN'
        assert second_instance.url == second_instance_url
        assert second_instance.username == "other_user"
        assert second_instance.token == "other_api_token"
