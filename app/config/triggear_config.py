import os
import yaml
import logging


class TriggearConfig:
    RERUN_DEFAULT_TIME = 30

    def __init__(self):
        with open(os.getenv('CREDS_PATH'), 'r') as stream:
            config = yaml.load(stream)
            self.jenkins_url = config['jenkins_url']
            self.jenkins_user_id = config['jenkins_user_id']
            self.jenkins_api_token = config['jenkins_api_token']
            self.github_token = config['github_token']
            self.triggear_token = config['triggear_token']
        with open(os.getenv('CONFIG_PATH'), 'r') as stream:
            try:
                config = yaml.load(stream)
                self.rerun_time_limit = config['rerun_time_limit']
            except (yaml.YAMLError, KeyError) as exc:
                logging.exception(f"Config YAML parsing error: {exc}. Setting rerun_time_limit to default value {self.RERUN_DEFAULT_TIME}")
                self.rerun_time_limit = self.RERUN_DEFAULT_TIME
