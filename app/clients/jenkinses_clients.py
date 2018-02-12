import logging
from typing import Dict

import yaml

from app.clients.jenkins_client import JenkinsClient
from app.config.triggear_config import TriggearConfig
from app.exceptions.triggear_error import TriggearError


class JenkinsesClients:
    def __init__(self, config: TriggearConfig) -> None:
        self.config = config
        self.__jenkins_clients: Dict[str, JenkinsClient] = {}

    def get_jenkins(self, url: str) -> JenkinsClient:
        client = self.__jenkins_clients.get(url)
        if client is None:
            logging.warning(f'Missing client for {url} - will create one')
            self.__setup_jenkins_client(url)
        return self.__jenkins_clients[url]

    def __setup_jenkins_client(self, url: str) -> None:
        if self.config.jenkins_instances.get(url) is None:
            logging.warning(f'Missing Jenkins {url} in current config. Will reload the config to check for new instances')
            new_config = TriggearConfig()
            if new_config.jenkins_instances.get(url) is None:
                raise TriggearError(f'Jenkins {url} not defined in current config. Please add its definition to creds file')
            else:
                self.config = new_config
        self.__jenkins_clients[url] = JenkinsClient(self.config.jenkins_instances[url])
