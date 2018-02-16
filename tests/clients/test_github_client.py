import asyncio
from typing import List

import pytest
from aiohttp import ClientResponse
from mockito import mock, expect, when, captor

from app.clients.async_client import AsyncClient, AsyncClientException, Payload, AsyncClientNotFoundException
from app.clients.github_client import GithubClient
from app.exceptions.triggear_timeout_error import TriggearTimeoutError
from tests.async_mockito import async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestGithubClient:
    async def test__when_get_async_github_is_issued__new_github_client_should_be_created(self):
        token = 'token'
        async_client = GithubClient(token).get_async_github()
        assert isinstance(async_client, AsyncClient)
        assert async_client.base_url == 'https://api.github.com'
        assert async_client.session_headers == {
            'Authorization': f'token {token}',
            'Content-Type': 'application/json'
        }

    async def test__when_async_github_api_client_was_created__it_is_returned_instead_of_creating_new(self):
        token = 'token'
        github_client = GithubClient(token)
        async_client = github_client.get_async_github()

        assert github_client.get_async_github() == async_client

    async def test__when_setting_pr_sync_label__if_github_raises_more_then_3_times__timeout_error_should_be_raised(self):
        github_client = GithubClient(mock())
        mock(spec=asyncio)

        # when
        when(github_client).add_to_pr_labels(repo='repo', number=43, label='triggear-pr-sync') \
            .thenRaise(AsyncClientException('Repo not found', 404))\
            .thenRaise(AsyncClientException('Repo not found', 404))\
            .thenRaise(AsyncClientException('Repo not found', 404))
        when(asyncio).sleep(1)\
            .thenReturn(async_value(None))\
            .thenReturn(async_value(None))\
            .thenReturn(async_value(None))

        # then
        with pytest.raises(TriggearTimeoutError) as timeout_error:
            await github_client.set_pr_sync_label_with_retry('repo', 43)
        assert str(timeout_error.value) == 'Failed to set label on PR #43 in repo repo after 3 retries'

    async def test__when_setting_pr_sync_label__if_github_returns_proper_objects__pr_sync_label_should_be_set(self):
        github_client = GithubClient(mock())

        # given
        expect(github_client).add_to_pr_labels(repo='repo', number=43, label='triggear-pr-sync').thenReturn(async_value(None))

        # when
        result = await github_client.set_pr_sync_label_with_retry('repo', 43)

        # then
        assert result is None

    async def test__when_get_repo_labels_is_called__only_label_names_are_returned(self):
        async_github: AsyncClient = mock(spec=AsyncClient, strict=True)
        github_client = GithubClient(mock())

        # given
        when(github_client).get_async_github().thenReturn(async_github)
        expect(async_github).get(route='/repos/repo/labels').thenReturn(async_value([{'name': 'label'}, {'name': 'other_label'}]))

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
        labels = {'labels': [{'name': 'label'}, {'name': 'other_label'}]}
        github_client = GithubClient(mock())

        expect(github_client).get_issue(repo='repo', number=25).thenReturn(async_value(labels))

        labels: List[str] = await github_client.get_pr_labels('repo', 25)

        assert ['label', 'other_label'] == labels

    async def test__get_latest_commit_sha__should_call_proper_github_entities(self):
        github_client = GithubClient(mock())

        expect(github_client).get_pull_request(repo='triggear', number=32).thenReturn(async_value({'head': {'sha': '123zxc'}}))

        sha: str = await github_client.get_latest_commit_sha('triggear', 32)

        assert '123zxc' == sha

    async def test__get_pr_branch__should_call_proper_github_entities(self):
        github_client = GithubClient(mock())

        expect(github_client).get_pull_request(repo='triggear', number=32).thenReturn(async_value({'head': {'ref': 'release'}}))

        sha: str = await github_client.get_pr_branch('triggear', 32)

        assert 'release' == sha

    async def test__get_file_content__should_call_proper_github_entities(self):
        async_github: AsyncClient = mock(spec=AsyncClient, strict=True)
        github_client = GithubClient(mock())

        # given
        when(github_client).get_async_github().thenReturn(async_github)
        arg_captor = captor()
        expect(async_github)\
            .get(route='/repos/triggear/contents/dir/file', params=arg_captor)\
            .thenReturn(async_value('content'))

        actual_response = await github_client.get_file_content('triggear', '123zxc', 'dir/file')

        assert actual_response == 'content'
        payload: Payload = arg_captor.value
        assert isinstance(payload, Payload)
        assert payload.data.get('ref') == '123zxc'

    async def test__create_pr_comment__calls_proper_github_entities(self):
        async_github: AsyncClient = mock(spec=AsyncClient, strict=True)
        github_client = GithubClient(mock())

        # given
        when(github_client).get_async_github().thenReturn(async_github)
        expect(github_client).get_commit_sha1(repo='repo', sha='123456').thenReturn(async_value('123456123456'))
        arg_captor = captor()
        expect(async_github)\
            .post(route='/repos/repo/commits/123456123456/comments', payload=arg_captor)\
            .thenReturn(async_value(None))

        await github_client.create_comment('repo', '123456', 'comment body')

        payload: Payload = arg_captor.value
        assert isinstance(payload, Payload)
        assert payload.data.get('body') == 'comment body'

    async def test__create_github_build_status__calls_github_client_properly(self):
        async_github: AsyncClient = mock(spec=AsyncClient, strict=True)
        github_client = GithubClient(mock())

        # given
        when(github_client).get_async_github().thenReturn(async_github)
        expect(github_client).get_commit_sha1(repo='repo', sha='123456').thenReturn(async_value('123456123456'))
        arg_captor = captor()
        expect(async_github)\
            .post(route='/repos/repo/statuses/123456123456', payload=arg_captor)\
            .thenReturn(async_value(None))

        await github_client.create_github_build_status('repo', '123456', 'pending', 'http://example.com', 'whatever you need', 'job')

        payload: Payload = arg_captor.value
        assert isinstance(payload, Payload)
        assert payload.data.get('state') == 'pending'
        assert payload.data.get('target_url') == 'http://example.com'
        assert payload.data.get('description') == 'whatever you need'
        assert payload.data.get('context') == 'job'

    async def test__get_issue__calls_github_endpoint_properly(self):
        async_github: AsyncClient = mock(spec=AsyncClient, strict=True)
        github_client = GithubClient(mock())

        when(github_client).get_async_github().thenReturn(async_github)
        expect(async_github).get(route='/repos/repo/issues/23').thenReturn(async_value({}))

        actual_response = await github_client.get_issue('repo', 23)
        assert actual_response == {}

    async def test__get_pull_request__calls_github_endpoint_properly(self):
        async_github: AsyncClient = mock(spec=AsyncClient, strict=True)
        github_client = GithubClient(mock())

        when(github_client).get_async_github().thenReturn(async_github)
        expect(async_github).get(route='/repos/repo/pulls/23').thenReturn(async_value({}))

        actual_response = await github_client.get_pull_request('repo', 23)
        assert actual_response == {}

    async def test__get_commit__calls_github_endpoint_properly(self):
        async_github: AsyncClient = mock(spec=AsyncClient, strict=True)
        github_client = GithubClient(mock())

        when(github_client).get_async_github().thenReturn(async_github)
        expect(async_github).get(route='/repos/repo/commits/123123').thenReturn(async_value({}))

        actual_response = await github_client.get_commit('repo', '123123')
        assert actual_response == {}

    async def test__get_commit_sha1__calls_github_endpoint_properly__when_sha_len_is_not_40(self):
        github_client = GithubClient(mock())

        expect(github_client).get_commit(repo='repo', sha='123123').thenReturn(async_value({'sha': '123123123123'}))

        assert '123123123123' == await github_client.get_commit_sha1('repo', '123123')

    async def test__get_commit_sha1__returns_unchanged_sha__when_sha_len_is_40(self):
        github_client = GithubClient(mock())

        sha_with_len_40 = '12312' * 8
        expect(github_client, times=0).get_commit(repo='repo', sha=sha_with_len_40)

        assert sha_with_len_40 == await github_client.get_commit_sha1('repo', sha_with_len_40)

    async def test__add_to_pr_labels__calls_github_endpoint_properly(self):
        async_github: AsyncClient = mock(spec=AsyncClient, strict=True)
        github_client = GithubClient(mock())

        when(github_client).get_async_github().thenReturn(async_github)
        arg_captor = captor()
        expect(async_github).post(route='/repos/repo/issues/23/labels', payload=arg_captor).thenReturn(async_value({}))

        actual_response = await github_client.add_to_pr_labels('repo', 23, 'some-label')
        assert actual_response == {}
        assert isinstance(arg_captor.value, Payload)
        assert arg_captor.value.data == ('some-label',)

    async def test__create_deployment__calls_github_client_properly(self):
        async_github: AsyncClient = mock(spec=AsyncClient, strict=True)
        github_client = GithubClient(mock())

        # given
        when(github_client).get_async_github().thenReturn(async_github)
        arg_captor = captor()
        expect(async_github)\
            .post(route='/repos/repo/deployments', payload=arg_captor)\
            .thenReturn(async_value(None))

        assert await github_client.create_deployment('repo', '123456', 'staging', 'something mildly interesting') is None

        payload: Payload = arg_captor.value
        assert isinstance(payload, Payload)
        assert payload.data.get('ref') == '123456'
        assert not payload.data.get('auto_merge')
        assert payload.data.get('description') == 'something mildly interesting'
        assert payload.data.get('environment') == 'staging'

    async def test__get_deployment__calls_github_endpoint_properly(self):
        async_github: AsyncClient = mock(spec=AsyncClient, strict=True)
        github_client = GithubClient(mock())

        when(github_client).get_async_github().thenReturn(async_github)
        arg_captor = captor()
        expect(async_github).get(route='/repos/repo/deployments', params=arg_captor).thenReturn(async_value({}))

        assert await github_client.get_deployments('repo', '123123', 'staging') == []
        params: Payload = arg_captor.value
        assert isinstance(params, Payload)
        assert params.data.get('ref') == '123123'
        assert params.data.get('environment') == 'staging'

    async def test__create_deployment_status__calls_github_client_properly(self):
        async_github: AsyncClient = mock(spec=AsyncClient, strict=True)
        github_client = GithubClient(mock())

        # given
        when(github_client).get_async_github().thenReturn(async_github)
        arg_captor = captor()
        expect(async_github)\
            .post(route='/repos/repo/deployments/123/statuses', payload=arg_captor)\
            .thenReturn(async_value(None))

        assert await github_client.create_deployment_status(repo='repo',
                                                            deployment_id=123,
                                                            state='success',
                                                            target_url='http://app.futuresimple.com',
                                                            description='something mildly interesting') is None

        payload: Payload = arg_captor.value
        assert isinstance(payload, Payload)
        assert payload.data.get('state') == 'success'
        assert payload.data.get('target_url') == 'http://app.futuresimple.com'
        assert payload.data.get('description') == 'something mildly interesting'

    async def test__are_files_in_repo__returns_true_if_all_files_exist(self):
        github_client = GithubClient(mock())

        expect(github_client).get_file_content(repo='repo', ref='123321', path='.gitignore').thenReturn(async_value("content"))
        expect(github_client).get_file_content(repo='repo', ref='123321', path='README.md').thenReturn(async_value("content"))

        assert await github_client.are_files_in_repo('repo', '123321', ['.gitignore', 'README.md'])

    async def test__are_files_in_repo__returns_false_if_any_of_files_is_missing(self):
        github_client = GithubClient(mock())

        expect(github_client).get_file_content(repo='repo', ref='123321', path='.gitignore').thenReturn(async_value("content"))
        expect(github_client).get_file_content(repo='repo', ref='123321', path='README.md').thenRaise(AsyncClientNotFoundException('file not found'))

        assert not await github_client.are_files_in_repo('repo', '123321', ['.gitignore', 'README.md'])

    async def test__get_branch_and_sha_from_pr_hook(self):
        data = {'repository': {'full_name': 'triggear'}, 'issue': {'number': 23}}
        github_client = GithubClient(mock())

        expect(github_client).get_pr_branch('triggear', 23).thenReturn(async_value('master'))
        expect(github_client).get_latest_commit_sha('triggear', 23).thenReturn(async_value('123321'))

        result = await github_client.get_pr_comment_branch_and_sha(data)
        assert result[0] == 'master'
        assert result[1] == '123321'
