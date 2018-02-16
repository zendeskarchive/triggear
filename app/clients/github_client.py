import asyncio
import logging
from typing import List, Dict, Tuple, Optional

from app.clients.async_client import AsyncClient, Payload, AsyncClientException
from app.enums.triggear_pr_label import TriggearPrLabel
from app.exceptions.triggear_timeout_error import TriggearTimeoutError


class GithubClient:
    def __init__(self, token: str) -> None:
        self.token: str = token
        self.__async_github: Optional[AsyncClient] = None

    def get_async_github(self) -> AsyncClient:
        if self.__async_github is None:
            self.__async_github: AsyncClient = AsyncClient(
                base_url='https://api.github.com',
                session_headers={
                    'Authorization': f'token {self.token}',
                    'Content-Type': 'application/json'
                }
            )
        return self.__async_github

    async def get_issue(self,
                        repo: str,
                        number: int) -> Dict:
        route = f'/repos/{repo}/issues/{number}'
        return await self.get_async_github().get(route=route)

    async def get_pull_request(self,
                               repo: str,
                               number: int) -> Dict:
        route = f'/repos/{repo}/pulls/{number}'
        return await self.get_async_github().get(route=route)

    async def get_commit(self,
                         repo: str,
                         sha: str) -> Dict:
        route = f'/repos/{repo}/commits/{sha}'
        return await self.get_async_github().get(route=route)

    async def get_file_content(self,
                               repo: str,
                               ref: str,
                               path: str) -> Dict:
        route = f'/repos/{repo}/contents/{path}'
        params = Payload.from_kwargs(
            ref=ref
        )
        return await self.get_async_github().get(route=route, params=params)

    async def get_commit_sha1(self,
                              repo: str,
                              sha: str) -> str:
        if len(sha) == 40:
            return sha
        commit_data = await self.get_commit(repo=repo, sha=sha)
        return str(commit_data['sha'])

    async def get_repo_labels(self,
                              repo: str) -> List[str]:
        route = f'/repos/{repo}/labels'
        labels_data = await self.get_async_github().get(route=route)
        return [label['name'] for label in labels_data]

    async def get_pr_labels(self,
                            repo: str,
                            number: int) -> List[str]:
        issue_data = await self.get_issue(repo=repo, number=number)
        return [label['name'] for label in issue_data['labels']]

    async def get_latest_commit_sha(self,
                                    repo: str,
                                    number: int) -> str:
        pr_data = await self.get_pull_request(repo=repo, number=number)
        return str(pr_data['head']['sha'])

    async def get_pr_branch(self,
                            repo: str,
                            number: int) -> str:
        pr_data = await self.get_pull_request(repo=repo, number=number)
        return str(pr_data['head']['ref'])

    async def set_sync_label(self,
                             repo: str,
                             number: int) -> None:
        if TriggearPrLabel.PR_SYNC in await self.get_repo_labels(repo):
            logging.warning(f'Setting "triggear-pr-sync" label on PR {number} in repo {repo}')
            await self.set_pr_sync_label_with_retry(repo, number)
            logging.warning('Label set')

    async def set_pr_sync_label_with_retry(self,
                                           repo: str,
                                           number: int) -> None:
        retries = 3
        while retries:
            try:
                await self.add_to_pr_labels(repo=repo, number=number, label=TriggearPrLabel.PR_SYNC.label_name)
                return
            except AsyncClientException as gh_exception:
                logging.exception(f'Exception when trying to set label on PR. Exception: {gh_exception}')
                retries -= 1
                await asyncio.sleep(1)
        raise TriggearTimeoutError(f'Failed to set label on PR #{number} in repo {repo} after 3 retries')

    async def add_to_pr_labels(self,
                               repo: str,
                               number: int,
                               label: str) -> Dict:
        route = f'/repos/{repo}/issues/{number}/labels'
        payload = Payload.from_args(label)
        return await self.get_async_github().post(route=route, payload=payload)

    async def create_comment(self,
                             repo: str,
                             sha: str,
                             body: str) -> Dict:
        sha1 = await self.get_commit_sha1(repo=repo, sha=sha)
        route = f'/repos/{repo}/commits/{sha1}/comments'
        payload = Payload.from_kwargs(
            body=body
        )
        return await self.get_async_github().post(route=route, payload=payload)

    async def create_github_build_status(self,
                                         repo: str,
                                         sha: str,
                                         state: str,
                                         url: str,
                                         description: str,
                                         context: str) -> Dict:
        sha1 = await self.get_commit_sha1(repo=repo, sha=sha)
        route = f'/repos/{repo}/statuses/{sha1}'
        payload = Payload.from_kwargs(
            state=state,
            target_url=url,
            description=description,
            context=context
        )
        return await self.get_async_github().post(route=route, payload=payload)

    async def create_deployment(self,
                                repo: str,
                                ref: str,
                                environment: str,
                                description: str) -> Dict:
        route = f'/repos/{repo}/deployments'
        payload = Payload.from_kwargs(
            ref=ref,
            auto_merge=False,
            environment=environment,
            description=description
        )
        return await self.get_async_github().post(route=route, payload=payload)

    async def get_deployments(self,
                              repo: str,
                              ref: Optional[str]=None,
                              environment: Optional[str]=None) -> List:
        route = f'/repos/{repo}/deployments'
        params = Payload.from_kwargs(
            ref=ref,
            environment=environment
        )
        return list(await self.get_async_github().get(route=route, params=params))

    async def create_deployment_status(self,
                                       repo: str,
                                       deployment_id: int,
                                       state: str,
                                       target_url: str,
                                       description: str='') -> Dict:
        route = f'/repos/{repo}/deployments/{deployment_id}/statuses'
        payload = Payload.from_kwargs(
            state=state,
            target_url=target_url,
            description=description
        )
        return await self.get_async_github().post(route=route, payload=payload)

    async def are_files_in_repo(self, repo: str, ref: str, files: List[str]) -> bool:
        try:
            for file in files:
                await self.get_file_content(repo=repo, ref=ref, path=file)
        except AsyncClientException:
            logging.exception(f"Exception when looking for file {file} in repo {repo} at ref {ref}")
            return False
        return True

    async def get_pr_comment_branch_and_sha(self, issue_comment_hook_data: Dict) -> Tuple[str, str]:
        repository_name = issue_comment_hook_data['repository']['full_name']
        pr_number = issue_comment_hook_data['issue']['number']
        head_branch = await self.get_pr_branch(repository_name, pr_number)
        head_sha = await self.get_latest_commit_sha(repository_name, pr_number)
        return head_branch, head_sha
