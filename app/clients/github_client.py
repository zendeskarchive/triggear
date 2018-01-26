import asyncio
import logging
from typing import List

import github

from app.enums.labels import Labels
from app.exceptions.triggear_timeout_error import TriggearTimeoutError


class GithubClient:
    def __init__(self, token: str):
        self.token: str = token
        self.github: github.Github = None

    def get_github(self) -> github.Github:
        if self.github is None:
            self.github = github.Github(login_or_token=self.token)
        return self.github

    async def set_pr_sync_label_with_retry(self, repo, pr_number):
        retries = 3
        while retries:
            try:
                self.get_github().get_repo(repo).get_issue(pr_number).add_to_labels(Labels.pr_sync)
                return
            except github.GithubException as gh_exception:
                logging.exception(f'Exception when trying to set label on PR. Exception: {gh_exception}')
                retries -= 1
                await asyncio.sleep(1)
        raise TriggearTimeoutError(f'Failed to set label on PR #{pr_number} in repo {repo} after 3 retries')

    async def get_repo_labels(self, repo: str):
        return [label.name for label in self.get_github().get_repo(repo).get_labels()]

    async def set_sync_label(self, repository, pr_number):
        if Labels.pr_sync in await self.get_repo_labels(repository):
            logging.warning(f'Setting "triggear-pr-sync" label on PR {pr_number} in repo {repository}')
            await self.set_pr_sync_label_with_retry(repository, pr_number)
            logging.warning('Label set')

    async def get_pr_labels(self, repository, pr_number) -> List[str]:
        return [label.name for label in self.get_github().get_repo(repository).get_issue(pr_number).labels]

    async def get_latest_commit_sha(self, pr_number: int, repository_name: str) -> str:
        return self.get_github().get_repo(repository_name).get_pull(pr_number).head.sha

    async def get_pr_branch(self, pr_number: int, repository_name: str) -> str:
        return self.get_github().get_repo(repository_name).get_pull(pr_number).head.ref

    async def get_file_content(self, path: str, repo: str, ref: str) -> str:
        return self.get_github().get_repo(repo).get_file_contents(path=path, ref=ref).content

    async def create_comment(self, repo: str, sha: str, body: str):
        self.get_github().get_repo(repo).get_commit(sha).create_comment(body=body)

    async def create_github_build_status(self, repository: str, sha: str, state: str, url: str, description: str, context: str):
        self.get_github().get_repo(repository).get_commit(sha).create_status(state=state,
                                                                             target_url=url,
                                                                             description=description,
                                                                             context=context)
