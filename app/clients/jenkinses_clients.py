import logging
from typing import Dict

import yaml

from app.clients.jenkins_client import JenkinsClient
from app.config.triggear_config import TriggearConfig
from app.exceptions.triggear_error import TriggearError


class JenkinsesClients:
    def __init__(self, config: TriggearConfig):
        self.config = config
        self.__jenkins_clients: Dict[str, JenkinsClient] = {}

    def get_jenkins(self, url: str) -> JenkinsClient:
        client = self.__jenkins_clients.get(url)
        if client is None:
            logging.warning(f'Missing client for {url} - will create one')
            self.setup_jenkins_client(url)
        return self.__jenkins_clients.get(url)

    def setup_jenkins_client(self, url: str):
        if self.config.jenkins_instances.get(url) is None:
            logging.warning(f'Missing Jenkins {url} in current config. Will reload the config to check for new instances')
            try:
                new_config = TriggearConfig()
                if new_config.jenkins_instances.get(url) is None:
                    raise TriggearError(f'Jenkins {url} not defined in current config. Please add its definition to creds file')
                else:
                    self.config = new_config
            except (yaml.YAMLError, KeyError):
                logging.exception('Exception caught when trying to reconfigure for new Jenkins instance in GithubController.'
                                  'Please check validity of provided config. Sticking with old one for now.')
                raise
        self.__jenkins_clients[url] = JenkinsClient(self.config.jenkins_instances.get(url))
