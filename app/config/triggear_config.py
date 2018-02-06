import os
from typing import List, Dict, Optional

import yaml

from app.clients.jenkins_client import JenkinsInstanceConfig


class TriggearConfig:
    def __init__(self) -> None:
        self.jenkins_instances: Dict[str, JenkinsInstanceConfig] = {}
        self.__github_token: str = None
        self.__triggear_token: str = None

    @property
    def github_token(self) -> str:
        if self.__github_token is None:
            self.read_credentials_from_creds()
        return self.__github_token

    @property
    def triggear_token(self) -> str:
        if self.__triggear_token is None:
            self.read_credentials_from_creds()
        return self.__triggear_token

    def read_credentials_from_creds(self) -> None:
        with open(os.getenv('CREDS_PATH', 'creds.yml'), 'r') as stream:
            config = yaml.load(stream)
            instances_config: List[Dict[str, str]] = config['jenkins_instances']
            for instance_config in instances_config:
                url = instance_config['url']
                user = instance_config['user']
                token = instance_config['token']
                self.jenkins_instances[url] = JenkinsInstanceConfig(url, user, token)
            self.__github_token = config['github_token']
            self.__triggear_token = config['triggear_token']
