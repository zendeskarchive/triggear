import os

import github
import jenkins
import motor.motor_asyncio

from aiohttp import web

from app.pipeline_handler import PipelineHandler
from app.triggear_config import TriggearConfig
from app.github_handler import GithubHandler


def main():
    app_config = TriggearConfig()

    gh_client = github.Github(login_or_token=app_config.github_token)
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient() if not os.environ.get('COMPOSE') == 'true' \
        else motor.motor_asyncio.AsyncIOMotorClient('mongodb://mongodb:27017')
    jenkins_client = jenkins.Jenkins(url=app_config.jenkins_url,
                                     username=app_config.jenkins_user_id,
                                     password=app_config.jenkins_api_token)
    rerun_time_limit = app_config.rerun_time_limit

    github_handler = GithubHandler(github_client=gh_client,
                                   mongo_client=mongo_client,
                                   jenkins_client=jenkins_client,
                                   rerun_time_limit=rerun_time_limit,
                                   api_token=app_config.triggear_token)
    register_handler = PipelineHandler(github_client=gh_client,
                                       mongo_client=mongo_client,
                                       api_token=app_config.triggear_token)

    app = web.Application()
    app.router.add_post('/github', github_handler.handle_hook)
    app.router.add_post('/register', register_handler.handle_register)
    app.router.add_post('/status', register_handler.handle_status)
    app.router.add_post('/comment', register_handler.handle_comment)
    web.run_app(app)


if __name__ == "__main__":
    main()
