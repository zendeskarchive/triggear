import pytest
from aiohttp.web_urldispatcher import UrlDispatcher

import app.config.triggear_config
import app.controllers.github_controller
import app.controllers.pipeline_controller
import app.controllers.health_controller
from mockito import when, mock, expect
from aiohttp import web
import motor.motor_asyncio
import app.clients.jenkins_client
import app.clients.github_client
import app.clients.mongo_client
import app.clients.jenkinses_clients
import app.triggear_heart
import app.middlewares.authentication_middleware
from app.middlewares.exceptions_middleware import exceptions

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestMain:
    async def test__main_app_flow(self):
        triggear_config = mock({
                'github_token': 'gh_token',
                'jenkins_url': 'url',
                'jenkins_user_id': 'user',
                'jenkins_api_token': 'jenkins_token',
                'triggear_token': 'triggear_token',
                'rerun_time_limit': 1
            },
            spec=app.config.triggear_config.TriggearConfig, strict=True)
        github_controller = mock({
                'handle_hook': 'hook_handler_method'
            },
            spec=app.controllers.github_controller.GithubController, strict=True)
        pipeline_controller = mock({
                'handle_register': 'register_handle_method',
                'handle_status': 'status_handle_method',
                'handle_comment': 'comment_handle_method',
                'handle_missing': 'missing_handle_method',
                'handle_deregister': 'deregister_handle_method',
                'handle_clear': 'clear_handle_method',
                'handle_deployment': 'deployment_handle_method',
                'handle_deployment_status': 'deployment_status_handle_method'
            },
            spec=app.controllers.pipeline_controller.PipelineController, strict=True)
        health_controller = mock({
                'handle_health_check': 'health_handle_method'
            },
            spec=app.controllers.health_controller.HealthController, strict=True)

        router = mock(spec=UrlDispatcher, strict=True)
        web_app = mock({'router': router}, spec=web.Application, strict=True)
        github_client = mock(spec=app.clients.github_client.GithubClient, strict=True)
        motor_client = mock(spec=motor.motor_asyncio, strict=True)
        mongo_client = mock(spec=app.clients.mongo_client.MongoClient, strict=True)
        jenkinses_clients = mock(spec=app.clients.jenkinses_clients.JenkinsesClients, strict=True)
        triggear_heart = mock(spec=app.triggear_heart.TriggearHeart, strict=True)
        authentication_middleware = mock({'authentication': 'auth_method'},
                                         spec=app.middlewares.authentication_middleware.AuthenticationMiddleware, strict=True)

        # given
        expect(app.config.triggear_config)\
            .TriggearConfig()\
            .thenReturn(triggear_config)
        expect(motor.motor_asyncio)\
            .AsyncIOMotorClient('localhost:27017')\
            .thenReturn(motor_client)
        expect(app.clients.github_client)\
            .GithubClient('gh_token')\
            .thenReturn(github_client)
        expect(app.clients.mongo_client) \
            .MongoClient(mongo=motor_client) \
            .thenReturn(mongo_client)
        expect(app.clients.jenkinses_clients) \
            .JenkinsesClients(triggear_config) \
            .thenReturn(jenkinses_clients)
        expect(app.triggear_heart) \
            .TriggearHeart(mongo_client, github_client, jenkinses_clients) \
            .thenReturn(triggear_heart)

        expect(app.controllers.github_controller)\
            .GithubController(triggear_heart=triggear_heart,
                              github_client=github_client,
                              config=triggear_config)\
            .thenReturn(github_controller)
        expect(app.controllers.pipeline_controller)\
            .PipelineController(github_client=github_client,
                                mongo_client=mongo_client)\
            .thenReturn(pipeline_controller)
        expect(app.controllers.health_controller)\
            .HealthController()\
            .thenReturn(health_controller)
        expect(app.middlewares.authentication_middleware) \
            .AuthenticationMiddleware(config=triggear_config) \
            .thenReturn(authentication_middleware)

        expect(web)\
            .Application(middlewares=(authentication_middleware.authentication, exceptions))\
            .thenReturn(web_app)

        expect(router).add_post('/github', 'hook_handler_method')
        expect(router).add_post('/register', 'register_handle_method')
        expect(router).add_post('/status', 'status_handle_method')
        expect(router).add_post('/comment', 'comment_handle_method')
        expect(router).add_get('/health', 'health_handle_method')
        expect(router).add_get('/missing/{eventType}', 'missing_handle_method')
        expect(router).add_post('/deregister', 'deregister_handle_method')
        expect(router).add_post('/clear', 'clear_handle_method')
        expect(router).add_post('/deployment', 'deployment_handle_method')
        expect(router).add_post('/deployment_status', 'deployment_status_handle_method')

        when(web).run_app(web_app)

        # then
        from app.main import main
        main()
