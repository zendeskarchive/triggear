import asyncio
from typing import List

import pytest
import github
import github.Repository
import github.Issue
import github.Label
import github.PullRequest
import github.PullRequestPart
import github.ContentFile
import github.Commit
from mockito import mock, expect, when

from app.clients.github_client import GithubClient
from app.exceptions.triggear_timeout_error import TriggearTimeoutError
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestGithubClient:
    async def test__when_get_github_is_issued__new_github_client_should_be_created(self):
        token = 'token'
        github_api_client = mock(spec=github.Github, strict=True)

        expect(github, times=1).Github(login_or_token=token).thenReturn(github_api_client)
        github_client = GithubClient(token)
        assert github_client.get_github() == github_api_client

    async def test__when_github_api_client_was_created__it_is_returned_instead_of_creating_new(self):
        token = 'token'
        github_api_client = mock(spec=github.Github, strict=True)

        expect(github, times=1).Github(login_or_token=token).thenReturn(github_api_client)
        github_client = GithubClient(token)
        github_client.get_github()

        expect(github, times=0).Github(login_or_token=token).thenReturn(github_api_client)
        assert github_client.get_github() == github_api_client

    async def test__when_setting_pr_sync_label__if_github_raises_more_then_3_times__timeout_error_should_be_raised(self):
        github_api_client: github.Github = mock(spec=github.Github, strict=True)
        github_client = GithubClient(mock())
        github_repository: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        mock(spec=asyncio)

        # when
        when(github_client).get_github().thenReturn(github_api_client)
        when(github_api_client).get_repo('repo')\
            .thenRaise(github.GithubException(404, 'repo not found'))\
            .thenRaise(github.GithubException(404, 'repo not found'))\
            .thenReturn(github_repository)
        when(github_repository).get_issue(43)\
            .thenRaise(github.GithubException(404, 'repo not found'))
        when(asyncio).sleep(1)\
            .thenReturn(async_value(None))\
            .thenReturn(async_value(None))\
            .thenReturn(async_value(None))

        # then
        with pytest.raises(TriggearTimeoutError) as timeout_error:
            await github_client.set_pr_sync_label_with_retry('repo', 43)
        assert str(timeout_error.value) == 'Failed to set label on PR #43 in repo repo after 3 retries'

    async def test__when_setting_pr_sync_label__if_github_returns_proper_objects__pr_sync_label_should_be_set(self):
        github_api_client: github.Github = mock(spec=github.Github, strict=True)
        github_client = GithubClient(mock())
        github_repository: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_issue: github.Issue.Issue = mock(spec=github.Issue.Issue, strict=True)

        # given
        when(github_client).get_github().thenReturn(github_api_client)
        when(github_api_client).get_repo('repo')\
            .thenReturn(github_repository)
        when(github_repository).get_issue(43)\
            .thenReturn(github_issue)
        expect(github_issue, times=1)\
            .add_to_labels('triggear-pr-sync')

        # when
        result = await github_client.set_pr_sync_label_with_retry('repo', 43)

        # then
        assert result is None

    async def test__when_get_repo_labels_is_called__only_label_names_are_returned(self):
        github_api_client: github.Github = mock(spec=github.Github, strict=True)
        github_client = GithubClient(mock())
        github_repository: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        label: github.Label.Label = mock({'name': 'label'}, spec=github.Label.Label, strict=True)
        other_label: github.Label.Label = mock({'name': 'other_label'}, spec=github.Label.Label, strict=True)

        # given
        when(github_client).get_github().thenReturn(github_api_client)
        when(github_api_client).get_repo('repo')\
            .thenReturn(github_repository)
        when(github_repository).get_labels()\
            .thenReturn([label, other_label])

        # when
        result: List[str] = await github_client.get_repo_labels('repo')

        # then
        assert result == ['label', 'other_label']

    async def test__when_repo_has_pr_sync_label__it_should_be_set(self):
        github_client = GithubClient(mock())

        # when
        when(github_client).get_repo_labels('repo').thenReturn(async_value(['label', 'triggear-pr-sync', 'other-label']))
        expect(github_client, times=1).set_pr_sync_label_with_retry('repo', 25).thenReturn(async_value(None))

        # then
        await github_client.set_sync_label('repo', 25)

    async def test__get_pr_labels__should_return_only_label_names(self):
        github_api_client: github.Github = mock(spec=github.Github, strict=True)
        github_client = GithubClient(mock())
        github_repository: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        label: github.Label.Label = mock({'name': 'label'}, spec=github.Label.Label, strict=True)
        other_label: github.Label.Label = mock({'name': 'other_label'}, spec=github.Label.Label, strict=True)
        github_issue: github.Issue.Issue = mock({'labels': [label, other_label]}, spec=github.Issue.Issue, strict=True)

        when(github_client).get_github().thenReturn(github_api_client)
        when(github_api_client).get_repo('repo')\
            .thenReturn(github_repository)
        when(github_repository).get_issue(25)\
            .thenReturn(github_issue)

        labels: List[str] = await github_client.get_pr_labels('repo', 25)

        assert ['label', 'other_label'] == labels

    async def test__get_latest_commit_sha__should_call_proper_github_entities(self):
        github_api_client: github.Github = mock(spec=github.Github, strict=True)
        github_repo: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_head: github.PullRequestPart.PullRequestPart = mock({'sha': '123zxc'}, spec=github.PullRequestPart, strict=True)
        github_pull_request: github.PullRequest.PullRequest = mock({'head': github_head}, spec=github.PullRequest.PullRequest, strict=True)
        github_client = GithubClient(mock())

        when(github_client).get_github().thenReturn(github_api_client)
        expect(github_api_client).get_repo('triggear').thenReturn(github_repo)
        expect(github_repo).get_pull(32).thenReturn(github_pull_request)

        sha: str = await github_client.get_latest_commit_sha(32, 'triggear')

        assert '123zxc' == sha

    async def test__get_pr_branch__should_call_proper_github_entities(self):
        github_api_client: github.Github = mock(spec=github.Github, strict=True)
        github_repo: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_head: github.PullRequestPart.PullRequestPart = mock({'ref': '123zxc'}, spec=github.PullRequestPart, strict=True)
        github_pull_request: github.PullRequest.PullRequest = mock({'head': github_head}, spec=github.PullRequest.PullRequest, strict=True)
        github_client = GithubClient(mock())

        when(github_client).get_github().thenReturn(github_api_client)
        expect(github_api_client).get_repo('triggear').thenReturn(github_repo)
        expect(github_repo).get_pull(32).thenReturn(github_pull_request)

        sha: str = await github_client.get_pr_branch(32, 'triggear')

        assert '123zxc' == sha

    async def test__get_file_content__should_call_proper_github_entities(self):
        github_api_client: github.Github = mock(spec=github.Github, strict=True)
        github_repo: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_file_content: github.ContentFile.ContentFile = mock({'content': 'content'}, spec=github.ContentFile.ContentFile, strict=True)
        github_client = GithubClient(mock())

        when(github_client).get_github().thenReturn(github_api_client)
        expect(github_api_client).get_repo('triggear').thenReturn(github_repo)
        expect(github_repo).get_file_contents(path='dir/file', ref='123zxc').thenReturn(github_file_content)

        content: str = await github_client.get_file_content('dir/file', 'triggear', '123zxc')

        assert 'content' == content

    async def test__create_pr_comment__calls_proper_github_entities(self):
        github_api_client: github.Github = mock(spec=github.Github, strict=True)
        github_repo: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_commit: github.Commit.Commit = mock(spec=github.Commit.Commit, strict=True)
        github_client = GithubClient(mock())

        when(github_client).get_github().thenReturn(github_api_client)
        expect(github_api_client).get_repo('repo').thenReturn(github_repo)
        expect(github_repo).get_commit('123456').thenReturn(github_commit)
        expect(github_commit).create_comment(body='comment body')

        await github_client.create_comment('repo', '123456', 'comment body')

    async def test__create_github_build_status__calls_github_client_properly(self):
        github_api_client: github.Github = mock(spec=github.Github, strict=True)
        github_repo: github.Repository.Repository = mock(spec=github.Repository.Repository, strict=True)
        github_commit: github.Commit.Commit = mock(spec=github.Commit.Commit, strict=True)
        github_client = GithubClient(mock())

        when(github_client).get_github().thenReturn(github_api_client)
        expect(github_api_client).get_repo('repo').thenReturn(github_repo)
        expect(github_repo).get_commit('123456').thenReturn(github_commit)
        expect(github_commit).create_status(state='pending',
                                            target_url='http://example.com',
                                            description='whatever you need',
                                            context='job')

        await github_client.create_github_build_status('repo', '123456', 'pending', 'http://example.com', 'whatever you need', 'job')
