import github
import pytest
import jenkins
from aiohttp.web_urldispatcher import UrlDispatcher

import app.config.triggear_config
import app.controllers.github_controller
import app.controllers.pipeline_controller
import app.controllers.health_controller
from mockito import when, mock, expect
from aiohttp import web
import motor.motor_asyncio

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
                'handle_clear': 'clear_handle_method'
            },
            spec=app.controllers.pipeline_controller.PipelineController, strict=True)
        health_controller = mock({
                'handle_health_check': 'health_handle_method'
            },
            spec=app.controllers.health_controller.HealthController, strict=True)

        router = mock(spec=UrlDispatcher, strict=True)
        web_app = mock({'router': router}, spec=web.Application, strict=True)
        github_client = mock(spec=github.Github, strict=True)
        mongo_client = mock(spec=motor.motor_asyncio, strict=True)
        jenkins_client = mock(spec=jenkins.Jenkins, strict=True)

        # given
        when(app.config.triggear_config)\
            .TriggearConfig()\
            .thenReturn(triggear_config)
        when(app.controllers.github_controller)\
            .GithubController(github_client=github_client,
                              mongo_client=mongo_client,
                              jenkins_client=jenkins_client,
                              config=triggear_config)\
            .thenReturn(github_controller)
        when(app.controllers.pipeline_controller)\
            .PipelineController(github_client=github_client,
                                mongo_client=mongo_client,
                                api_token='triggear_token')\
            .thenReturn(pipeline_controller)
        when(app.controllers.health_controller)\
            .HealthController(api_token='triggear_token')\
            .thenReturn(health_controller)

        when(web)\
            .Application()\
            .thenReturn(web_app)
        when(github)\
            .Github(login_or_token='gh_token')\
            .thenReturn(github_client)
        when(motor.motor_asyncio)\
            .AsyncIOMotorClient()\
            .thenReturn(mongo_client)
        when(jenkins)\
            .Jenkins(url='url', username='user', password='jenkins_token')\
            .thenReturn(jenkins_client)

        expect(router)\
            .add_post('/github', 'hook_handler_method')
        expect(router)\
            .add_post('/register', 'register_handle_method')
        expect(router)\
            .add_post('/status', 'status_handle_method')
        expect(router)\
            .add_post('/comment', 'comment_handle_method')
        expect(router)\
            .add_get('/health', 'health_handle_method')
        expect(router)\
            .add_get('/missing/{eventType}', 'missing_handle_method')
        expect(router)\
            .add_post('/deregister', 'deregister_handle_method')
        expect(router)\
            .add_post('/clear', 'clear_handle_method')

        when(web).run_app(web_app)

        # then
        from app.main import main
        main()
