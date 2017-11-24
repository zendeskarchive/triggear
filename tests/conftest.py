from unittest.mock import Mock

import pytest
from asynctest import patch
from pytest_mock import MockFixture
from typing import Dict
from typing import Tuple
from _asyncio import Task

from app.controllers.github_controller import GithubController
from app.utilities.background_task import BackgroundTask
from tests.goodies import AsyncIterFromList


@pytest.fixture
def background_task():
    yield BackgroundTask()


@pytest.fixture
def empty_coro():
    async def coro(*args, **kwargs) -> Tuple:
        return args, kwargs
    return Mock(wraps=coro)


@pytest.fixture
def exception_coro():
    # noinspection PyUnusedLocal
    async def coro(*args, **kwargs) -> None:
        raise Exception()
    return Mock(wraps=coro)


@pytest.fixture
def callback():
    def inner(future: Task) -> None:
        try:
            future.exception(None)
        except:
            pass
    return Mock(wraps=inner)


@pytest.fixture
def gh_sut(mocker: MockFixture):
    mock_jenkins = mocker.patch('app.controllers.github_controller.jenkins.Jenkins')
    mock_github = mocker.patch('app.controllers.github_controller.github.Github')
    mock_mongo = mocker.patch('motor.motor_asyncio.AsyncIOMotorClient')
    mock_config = mocker.patch('app.config.triggear_config.TriggearConfig')

    with patch('app.controllers.github_controller.asyncio.sleep'):
        yield GithubController(mock_github, mock_mongo, mock_jenkins, mock_config)


@pytest.fixture
def valid_synchronize_data():
    yield {'pull_request': {'head': {'repo': {'full_name': 'test_repo'}, 'sha': 'test_sha', 'ref': 'test_branch'},
                            'number': 'test_pr_number'}}


@pytest.fixture
def valid_pr_opened_data():
    yield {
        'pull_request': {'head': {'ref': 'test_branch', 'sha': 'test_sha'}, 'number': 38},
        'repository': {'full_name': 'test_repo'}
    }


@pytest.fixture
def valid_labeled_data():
    yield {'pull_request': {'head': {'sha': 'test_sha',
                                     'ref': 'test_branch',
                                     'repo': {'full_name': 'test_repo'}}},
           'label': {'name': 'test_label'}}


@pytest.fixture
def mock_trigger_registered_jobs(gh_sut):
    with patch.object(gh_sut, 'trigger_registered_jobs') as mock:
        yield mock


@pytest.fixture
def mock_trigger_registered_job(gh_sut):
    with patch.object(gh_sut, 'trigger_registered_job') as mock:
        yield mock


@pytest.fixture
def mock_trigger_unregistered_jobs(gh_sut):
    with patch.object(gh_sut, 'trigger_unregistered_job') as mock:
        yield mock


@pytest.fixture
def mock_can_trigger_job_by_branch(gh_sut):
    with patch.object(gh_sut, 'can_trigger_job_by_branch', return_value=True) as mock:
        yield mock


@pytest.fixture
def mock_cannot_trigger_job_by_branch(gh_sut):
    with patch.object(gh_sut, 'can_trigger_job_by_branch', return_value=False) as mock:
        yield mock


@pytest.fixture
def mock_is_job_building(gh_sut):
    with patch.object(gh_sut, 'is_job_building', side_effect=[True, False]) as mock:
        yield mock


@pytest.fixture
def mock_request():
    class ToTest:
        headers = {'X-GitHub-Event': 'event'}

        @staticmethod
        async def json() -> Dict:
            return {'json': 'json'}
    yield ToTest


@pytest.fixture
def mock_empty_collection():
    class Collection:
        @staticmethod
        def find(query):
            # type: (Dict[str, str]) -> AsyncIterFromList
            return AsyncIterFromList([])
    yield Collection


@pytest.fixture
def mock_two_elem_collection():
    class Collection:
        # noinspection PyUnusedLocal
        @staticmethod
        def find(query: Dict[str, str]) -> AsyncIterFromList:
            return AsyncIterFromList(
                [{'job': 'test_job_1', 'requested_params': [], 'repository': 'test_repo_1'},
                 {'job': 'test_job_2', 'requested_params': ['branch'], 'repository': 'test_repo_2'}]
            )

        @staticmethod
        async def delete_one(query: Dict[str, str]) -> None:
            return
    yield Collection


@pytest.fixture
def mock_collection_with_branch_restriction():
    class Collection:
        # noinspection PyUnusedLocal
        @staticmethod
        def find(query: Dict[str, str]) -> AsyncIterFromList:
            return AsyncIterFromList(
                [{'job': 'test_job_1',
                  'requested_params': [],
                  'repository': 'test_repo_1',
                  'branch_restrictions': ['master']}]
            )

        @staticmethod
        async def delete_one(query):
            return
    yield Collection


@pytest.fixture
def mock_collection_with_change_restriction():
    class Collection:
        # noinspection PyUnusedLocal
        @staticmethod
        def find(query: Dict[str, str]) -> AsyncIterFromList:
            return AsyncIterFromList(
                [{'job': 'test_job_1',
                  'requested_params': [],
                  'repository': 'test_repo_1',
                  'change_restrictions': ['some_file', 'another/directory']}]
            )

        @staticmethod
        async def delete_one(query):
            return
    yield Collection
