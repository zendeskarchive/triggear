import asyncio
import logging
from typing import Dict, Awaitable, List
from typing import Optional

import aiohttp.web
import aiohttp.web_request
from aiohttp.web_response import Response

from app.clients.github_client import GithubClient
from app.config.triggear_config import TriggearConfig
from app.data_objects.github_event import GithubEvent
from app.enums.event_types import EventType
from app.enums.triggear_pr_label import TriggearPrLabel
from app.hook_details.hook_details_factory import HookDetailsFactory
from app.hook_details.pr_opened_hook_details import PrOpenedHookDetails
from app.hook_details.push_hook_details import PushHookDetails
from app.hook_details.tag_hook_details import TagHookDetails
from app.triggear_heart import TriggearHeart
from app.utilities.constants import BRANCH_DELETED_SHA


class GithubController:
    GITHUB_EVENT_HEADER = 'X-GitHub-Event'

    def __init__(self,
                 config: TriggearConfig,
                 github_client: GithubClient,
                 triggear_heart: TriggearHeart) -> None:
        self.config = config
        self.__github_client = github_client
        self.__triggear_heart = triggear_heart

    async def handle_hook(self, request: aiohttp.web_request.Request) -> Optional[Response]:
        data = await request.json()
        github_event = GithubEvent(event_header=request.headers.get(self.GITHUB_EVENT_HEADER),
                                   action=data.get('action'),
                                   ref=data.get('ref'))
        logging.warning(f"Hook received: {github_event}")
        handler_task = self.get_event_handler_task(data, github_event)
        if handler_task is not None:
            asyncio.get_event_loop().create_task(handler_task)
        return aiohttp.web.Response(text='Hook ACK')

    def get_event_handler_task(self, data: Dict, github_event: GithubEvent) -> Optional[Awaitable]:
        if github_event == EventType.PR_LABELED:
            return self.handle_labeled(data)
        elif github_event == EventType.SYNCHRONIZE:
            return self.handle_synchronize(data)
        elif github_event == EventType.ISSUE_COMMENT:
            return self.handle_comment(data)
        elif github_event == EventType.PR_OPENED:
            return self.handle_pr_opened(data)
        elif github_event == EventType.PUSH:
            # return self.handle_push(data)
            return None
        elif github_event == EventType.TAGGED:
            return self.handle_tagged(data)
        elif github_event == EventType.RELEASE:
            # return self.handle_release(data)
            return None
        return None

    async def handle_release(self, data: Dict) -> None:
        await self.__triggear_heart.trigger_registered_jobs(HookDetailsFactory.get_release_details(data))

    async def handle_pr_opened(self, data: Dict) -> None:
        hook_details: PrOpenedHookDetails = HookDetailsFactory.get_pr_opened_details(data)
        await self.__github_client.set_sync_label(repo=hook_details.repository, number=data['pull_request']['number'])
        await self.__triggear_heart.trigger_registered_jobs(hook_details)

    async def handle_tagged(self, data: Dict) -> None:
        hook_details: TagHookDetails = HookDetailsFactory.get_tag_details(data)
        if hook_details.sha != BRANCH_DELETED_SHA:
            await self.__triggear_heart.trigger_registered_jobs(hook_details)
        else:
            logging.warning(f"Tag {hook_details.tag} was deleted as SHA was zeros only!")

    async def handle_labeled(self, data: Dict) -> None:
        await self.__triggear_heart.trigger_registered_jobs(HookDetailsFactory.get_labeled_details(data))

    async def handle_synchronize(self, data: Dict) -> None:
        pr_labels = await self.__github_client.get_pr_labels(repo=data['pull_request']['head']['repo']['full_name'],
                                                             number=data['pull_request']['number'])
        asyncio.gather(
            self.handle_pr_sync(data, pr_labels),
            self.handle_labeled_sync(data, pr_labels)
        )

    async def handle_pr_sync(self, data: Dict, pr_labels: List[str]) -> None:
        if TriggearPrLabel.PR_SYNC in pr_labels:
            logging.warning(f'Sync hook on PR with {TriggearPrLabel.PR_SYNC} - handling like PR open')
            await self.handle_pr_opened(data)

    async def handle_labeled_sync(self, data: Dict, pr_labels: List[str]) -> None:
        if TriggearPrLabel.LABEL_SYNC in pr_labels and len(pr_labels) > 1:
            pr_labels.remove(TriggearPrLabel.LABEL_SYNC.label_name)
            for label in pr_labels:
                # update data to have fields required from labeled hook
                # it's necessary for HookDetailsFactory in handle_labeled
                data.update({'label': {'name': label}})
                logging.warning(f'Sync hook on PR with {TriggearPrLabel.LABEL_SYNC} - handling like PR labeled')
                await self.handle_labeled(data)

    async def handle_comment(self, data: Dict) -> None:
        comment_body = data['comment']['body']
        branch, sha = await self.__github_client.get_pr_comment_branch_and_sha(data)
        if comment_body == TriggearPrLabel.LABEL_SYNC:
            await self.handle_labeled_sync_comment(data, branch, sha)
        elif comment_body == TriggearPrLabel.PR_SYNC:
            await self.handle_pr_sync_comment(data, branch, sha)

    async def handle_pr_sync_comment(self, data: Dict, branch: str, sha: str) -> None:
        await self.__triggear_heart.trigger_registered_jobs(HookDetailsFactory.get_pr_sync_details(data, branch, sha))

    async def handle_labeled_sync_comment(self, data: Dict, branch: str, sha: str) -> None:
        for hook_details in HookDetailsFactory.get_labeled_sync_details(data, head_branch=branch, head_sha=sha):
            await self.__triggear_heart.trigger_registered_jobs(hook_details)

    async def handle_push(self, data: Dict) -> None:
        hook_details: PushHookDetails = HookDetailsFactory.get_push_details(data)
        if hook_details.sha != BRANCH_DELETED_SHA:
            await self.__triggear_heart.trigger_registered_jobs(hook_details)
        else:
            logging.warning(f"Branch {hook_details.branch} was deleted as SHA was zeros only!")
