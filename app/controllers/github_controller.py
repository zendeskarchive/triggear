import asyncio
import hmac
import logging
from typing import Dict
from typing import Optional

import aiohttp.web
import aiohttp.web_request
from aiohttp.web_response import Response

from app.clients.github_client import GithubClient
from app.config.triggear_config import TriggearConfig
from app.enums.event_types import EventType
from app.enums.triggear_pr_label import TriggearPrLabel
from app.hook_details.hook_details_factory import HookDetailsFactory
from app.hook_details.pr_opened_hook_details import PrOpenedHookDetails
from app.hook_details.push_hook_details import PushHookDetails
from app.hook_details.tag_hook_details import TagHookDetails
from app.triggear_heart import TriggearHeart
from app.utilities.constants import BRANCH_DELETED_SHA
from app.utilities.err_handling import handle_exceptions


class GithubController:
    GITHUB_EVENT_HEADER = 'X-GitHub-Event'
    GITHUB_SIGNATURE_HEADER = 'X-Hub-Signature'

    def __init__(self,
                 config: TriggearConfig,
                 github_client: GithubClient,
                 triggear_heart: TriggearHeart):
        self.config = config
        self.__github_client = github_client
        self.__triggear_heart = triggear_heart

    async def validate_webhook_secret(self, req):
        header_signature = req.headers.get(self.GITHUB_SIGNATURE_HEADER)

        if header_signature is None:
            return 401, 'Unauthorized'
        sha_name, signature = header_signature.split('=')
        if sha_name != 'sha1':
            return 501, "Only SHA1 auth supported"

        req_body = await req.read()
        mac = hmac.new(bytearray(self.config.triggear_token, 'utf-8'), msg=req_body, digestmod='sha1')
        if not hmac.compare_digest(str(mac.hexdigest()), str(signature)):
            return 401, 'Unauthorized'
        return 'AUTHORIZED'

    @staticmethod
    async def get_request_json(request: aiohttp.web_request.Request) -> Dict:
        return await request.json()

    @handle_exceptions()
    async def handle_hook(self, request: aiohttp.web_request.Request) -> Optional[Response]:
        validation = await self.validate_webhook_secret(request)
        if validation != 'AUTHORIZED':
            return aiohttp.web.Response(text=validation[1], status=validation[0])

        data = await self.get_request_json(request)
        logging.warning(f"Hook received")

        action = data.get('action')
        triggear_task = None
        if action == EventType.labeled:
            triggear_task = self.handle_labeled(data)
        elif action == EventType.synchronize:
            triggear_task = self.handle_synchronize(data)
        elif action == EventType.comment:
            await self.handle_comment(data)
        else:
            event_header = request.headers.get(self.GITHUB_EVENT_HEADER)
            if event_header == EventType.pull_request:
                if action == EventType.pr_opened:
                    triggear_task = self.handle_pr_opened(data)
            elif event_header == EventType.push:
                if data['ref'].startswith('refs/heads/'):
                    triggear_task = self.handle_push(data)
                elif data['ref'].startswith('refs/tags/'):
                    triggear_task = self.handle_tagged(data)
            elif event_header == EventType.release:
                triggear_task = self.handle_release(data)
        asyncio.get_event_loop().create_task(triggear_task)
        return aiohttp.web.Response(text='Hook ACK')

    async def handle_release(self, data: Dict):
        await self.__triggear_heart.trigger_registered_jobs(HookDetailsFactory.get_release_details(data))

    async def handle_pr_opened(self, data: Dict):
        hook_details: PrOpenedHookDetails = HookDetailsFactory.get_pr_opened_details(data)
        await self.__github_client.set_sync_label(hook_details.repository, number=data['pull_request']['number'])
        await self.__triggear_heart.trigger_registered_jobs(hook_details)

    async def handle_tagged(self, data: dict):
        hook_details: TagHookDetails = HookDetailsFactory.get_tag_details(data)
        if hook_details.sha != BRANCH_DELETED_SHA:
            await self.__triggear_heart.trigger_registered_jobs(hook_details)
        else:
            logging.warning(f"Tag {hook_details.tag} was deleted as SHA was zeros only!")

    async def handle_labeled(self, data: dict):
        await self.__triggear_heart.trigger_registered_jobs(HookDetailsFactory.get_labeled_details(data))

    async def handle_synchronize(self, data: Dict):
        pr_labels = await self.__github_client.get_pr_labels(repo=data['pull_request']['head']['repo']['full_name'],
                                                             number=data['pull_request']['number'])
        asyncio.gather(
            self.handle_pr_sync(data, pr_labels),
            self.handle_labeled_sync(data, pr_labels)
        )

    async def handle_pr_sync(self, data, pr_labels):
        if TriggearPrLabel.PR_SYNC in pr_labels:
            logging.warning(f'Sync hook on PR with {TriggearPrLabel.PR_SYNC} - handling like PR open')
            await self.handle_pr_opened(data)

    async def handle_labeled_sync(self, data, pr_labels):
        if TriggearPrLabel.LABEL_SYNC in pr_labels and len(pr_labels) > 1:
            pr_labels.remove(TriggearPrLabel.LABEL_SYNC)
            for label in pr_labels:
                # update data to have fields required from labeled hook
                # it's necessary for HookDetailsFactory in handle_labeled
                data.update({'label': {'name': label}})
                logging.warning(f'Sync hook on PR with {TriggearPrLabel.LABEL_SYNC} - handling like PR labeled')
                await self.handle_labeled(data)

    async def handle_comment(self, data):
        comment_body = data['comment']['body']
        branch, sha = await self.__github_client.get_pr_comment_branch_and_sha(data)
        if comment_body == TriggearPrLabel.LABEL_SYNC:
            await self.handle_labeled_sync_comment(data, branch, sha)
        elif comment_body == TriggearPrLabel.PR_SYNC:
            await self.handle_pr_sync_comment(data, branch, sha)

    async def handle_pr_sync_comment(self, data: Dict, branch: str, sha: str):
        await self.__triggear_heart.trigger_registered_jobs(HookDetailsFactory.get_pr_sync_details(data, branch, sha))

    async def handle_labeled_sync_comment(self, data, branch: str, sha: str):
        for hook_details in HookDetailsFactory.get_labeled_sync_details(data, head_branch=branch, head_sha=sha):
            await self.__triggear_heart.trigger_registered_jobs(hook_details)

    async def handle_push(self, data):
        hook_details: PushHookDetails = HookDetailsFactory.get_push_details(data)
        if hook_details.sha != BRANCH_DELETED_SHA:
            await self.__triggear_heart.trigger_registered_jobs(hook_details)
        else:
            logging.warning(f"Branch {hook_details.branch} was deleted as SHA was zeros only!")
