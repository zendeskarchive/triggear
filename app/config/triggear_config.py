import os
from typing import List, Dict, Tuple, Optional

import yaml

from app.clients.jenkins_client import JenkinsInstanceConfig


class TriggearConfig:
    def __init__(self) -> None:
        self.__jenkins_instances: Dict[str, JenkinsInstanceConfig] = {}
        self.__github_token: Optional[str] = None
        self.__triggear_token: Optional[str] = None

    @property
    def jenkins_instances(self) -> Dict[str, JenkinsInstanceConfig]:
        if self.__jenkins_instances == {}:
            self.__github_token, self.__triggear_token, self.__jenkins_instances = self.read_credentials_file()
        return self.__jenkins_instances

    @property
    def github_token(self) -> str:
        if self.__github_token is None:
            self.__github_token, self.__triggear_token, self.__jenkins_instances = self.read_credentials_file()
        return self.__github_token

    @property
    def triggear_token(self) -> str:
        if self.__triggear_token is None:
            self.__github_token, self.__triggear_token, self.__jenkins_instances = self.read_credentials_file()
        return self.__triggear_token

    @staticmethod
    def read_credentials_file() -> Tuple[str, str, Dict[str, JenkinsInstanceConfig]]:
        with open(os.getenv('CREDS_PATH', 'creds.yml'), 'r') as stream:
            config = yaml.load(stream)
            instances_config: List[Dict[str, str]] = config['jenkins_instances']
            jenkins_instances: Dict[str, JenkinsInstanceConfig] = {}
            for instance_config in instances_config:
                url = instance_config['url']
                user = instance_config['user']
                token = instance_config['token']
                jenkins_instances[url] = JenkinsInstanceConfig(url, user, token)
            return config['github_token'], config['triggear_token'], jenkins_instances
