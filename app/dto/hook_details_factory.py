from typing import List, Dict

from app.dto.hook_details import HookDetails
from app.enums.event_types import EventTypes
from app.utilities.functions import flatten_list
from typing import Set


class HookDetailsFactory:
    @staticmethod
    def get_pr_opened_details(data: Dict) -> HookDetails:
        return HookDetails(
            event_type=EventTypes.pr_opened,
            repository=data['repository']['full_name'],
            branch=data['pull_request']['head']['ref'],
            sha=data['pull_request']['head']['sha']
        )

    @staticmethod
    def get_tag_details(data: Dict) -> HookDetails:
        hook_details = HookDetails(
            event_type=EventTypes.tagged,
            repository=data['repository']['full_name'],
            branch='',
            sha=data['after']
        )
        hook_details.tag = data['ref'][10:]
        return hook_details

    @staticmethod
    def get_push_details(data: Dict) -> HookDetails:
        hook_details = HookDetails(
            event_type=EventTypes.push,
            repository=data['repository']['full_name'],
            branch=data['ref'][11:] if data['ref'].startswith('refs/heads/') else data['ref'],
            sha=data['after']
        )
        hook_details.changes = HookDetailsFactory.__get_changes(data['commits'])
        return hook_details

    @staticmethod
    def __get_changes(commits: List[Dict]) -> Set[str]:
        additions = flatten_list([commit['added'] for commit in commits])
        removals = flatten_list([commit['removed'] for commit in commits])
        modifications = flatten_list([commit['modified'] for commit in commits])
        return set(additions + removals + modifications)

    @staticmethod
    def get_labeled_details(data) -> HookDetails:
        return HookDetails(
            event_type=EventTypes.labeled,
            repository=data['pull_request']['head']['repo']['full_name'],
            branch=data['pull_request']['head']['ref'],
            sha=data['pull_request']['head']['sha'],
            labels=data['label']['name']
        )

    @staticmethod
    def get_labeled_sync_details(data, head_branch: str, head_sha: str) -> List[HookDetails]:
        return [
            HookDetails(
                event_type=EventTypes.labeled,
                repository=data['repository']['full_name'],
                branch=head_branch,
                sha=head_sha,
                labels=label
            ) for label in [label['name'] for label in data['issue']['labels']]
        ]

    @staticmethod
    def get_pr_sync_details(data: Dict, head_branch: str, head_sha: str) -> HookDetails:
        return HookDetails(
            event_type=EventTypes.pr_opened,
            repository=data['repository']['full_name'],
            branch=head_branch,
            sha=head_sha
        )
