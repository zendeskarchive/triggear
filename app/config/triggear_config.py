import os
from typing import List, Dict

import yaml

from app.clients.jenkins_client import JenkinsInstanceConfig


class TriggearConfig:
    def __init__(self) -> None:
        self.jenkins_instances: Dict[str, JenkinsInstanceConfig] = {}
        self.github_token = None
        self.triggear_token = None
        self.read_credentials_from_creds()

    def read_credentials_from_creds(self):
        with open(os.getenv('CREDS_PATH'), 'r') as stream:
            config = yaml.load(stream)
            instances_config: List[Dict[str, Dict]] = config['jenkins_instances']
            for instance_config in instances_config:
                url = instance_config['url']
                user = instance_config['user']
                token = instance_config['token']
                self.jenkins_instances[url] = JenkinsInstanceConfig(url, user, token)
            self.github_token = config['github_token']
            self.triggear_token = config['triggear_token']
