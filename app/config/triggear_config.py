import os
import yaml
import logging


class TriggearConfig:
    def __init__(self):
        with open(os.environ['CREDS_PATH'], 'r') as stream:
            try:
                config = yaml.load(stream)
                self.jenkins_url = config['jenkins_url']
                self.jenkins_user_id = config['jenkins_user_id']
                self.jenkins_api_token = config['jenkins_api_token']
                self.github_token = config['github_token']
                self.triggear_token = config['triggear_token']
            except yaml.YAMLError as exc:
                logging.exception(f"Creds YAML parsing error: {exc}")
        with open(os.environ['CONFIG_PATH'], 'r') as stream:
            try:
                config = yaml.load(stream)
                self.rerun_time_limit = config['rerun_time_limit']
            except yaml.YAMLError as exc:
                logging.exception(f"Config YAML parsing error: {exc}")
                self.rerun_time_limit = 30
