import os

import motor.motor_asyncio
from aiohttp import web

from app.clients.github_client import GithubClient
from app.clients.jenkinses_clients import JenkinsesClients
from app.clients.mongo_client import MongoClient
from app.config.triggear_config import TriggearConfig
from app.controllers.github_controller import GithubController
from app.controllers.health_controller import HealthController
from app.controllers.pipeline_controller import PipelineController
from app.middlewares.authentication_middleware import AuthenticationMiddleware
from app.middlewares.exceptions_middleware import exceptions
from app.routes import Routes
from app.triggear_heart import TriggearHeart


def main() -> None:
    app_config = TriggearConfig()

    motor_mongo = motor.motor_asyncio.AsyncIOMotorClient() if not os.environ.get('COMPOSE') == 'true' \
        else motor.motor_asyncio.AsyncIOMotorClient('mongodb://mongodb:27017')

    gh_client = GithubClient(app_config.github_token)
    mongo_client = MongoClient(mongo=motor_mongo)
    jenkinses_clients = JenkinsesClients(app_config)
    triggear_heart = TriggearHeart(mongo_client, gh_client, jenkinses_clients)

    github_controller = GithubController(triggear_heart=triggear_heart, github_client=gh_client, config=app_config)
    pipeline_controller = PipelineController(github_client=gh_client, mongo_client=mongo_client)
    health_controller = HealthController()
    authentication_middleware = AuthenticationMiddleware(config=app_config)

    app = web.Application(middlewares=(authentication_middleware.authentication, exceptions))
    app.router.add_post(Routes.GITHUB.route, github_controller.handle_hook)
    app.router.add_post(Routes.REGISTER.route, pipeline_controller.handle_register)
    app.router.add_post(Routes.STATUS.route, pipeline_controller.handle_status)
    app.router.add_post(Routes.COMMENT.route, pipeline_controller.handle_comment)
    app.router.add_get(Routes.HEALTH.route, health_controller.handle_health_check)
    app.router.add_get(Routes.MISSING.route, pipeline_controller.handle_missing)
    app.router.add_post(Routes.DEREGISTER.route, pipeline_controller.handle_deregister)
    app.router.add_post(Routes.CLEAR.route, pipeline_controller.handle_clear)
    app.router.add_post(Routes.DEPLOYMENT.route, pipeline_controller.handle_deployment)
    app.router.add_post(Routes.DEPLOYMENT_STATUS.route, pipeline_controller.handle_deployment_status)

    web.run_app(app)


if __name__ == "__main__":  # pragma: no cover
    main()
