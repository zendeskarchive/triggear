import os
import logging
from typing import List, Dict

import yaml


class JenkinsInstanceConfig:
    def __init__(self, url, username, token):
        self.username: str = username
        self.token: str = token
        self.url = url


class TriggearConfig:
    RERUN_DEFAULT_TIME = 30

    def __init__(self):
        self.jenkins_instances: Dict[str, JenkinsInstanceConfig] = {}
        self.github_token = None
        self.triggear_token = None
        self.rerun_time_limit = self.RERUN_DEFAULT_TIME

        self.read_credentials_from_creds()
        self.read_rerun_time_limit_from_config()

    def read_rerun_time_limit_from_config(self):
        with open(os.getenv('CONFIG_PATH'), 'r') as stream:
            try:
                config = yaml.load(stream)
                self.rerun_time_limit = config['rerun_time_limit']
            except (yaml.YAMLError, KeyError) as exc:
                logging.exception(f"Config YAML parsing error: {exc}. Setting rerun_time_limit to default value {self.RERUN_DEFAULT_TIME}")
                self.rerun_time_limit = self.RERUN_DEFAULT_TIME

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
