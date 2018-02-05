from typing import List, Dict

from app.hook_details.labeled_hook_details import LabeledHookDetails
from app.hook_details.pr_opened_hook_details import PrOpenedHookDetails
from app.hook_details.push_hook_details import PushHookDetails
from app.hook_details.release_hook_details import ReleaseHookDetails
from app.hook_details.tag_hook_details import TagHookDetails
from app.utilities.functions import flatten_list
from typing import Set


class HookDetailsFactory:
    @staticmethod
    def get_labeled_sync_details(data, head_branch: str, head_sha: str) -> List[LabeledHookDetails]:
        return [
            LabeledHookDetails(
                repository=data['repository']['full_name'],
                branch=head_branch,
                sha=head_sha,
                label=label
            ) for label in [label['name'] for label in data['issue']['labels']]
        ]
    
    @staticmethod
    def get_pr_opened_details(data: Dict) -> PrOpenedHookDetails:
        return PrOpenedHookDetails(
            repository=data['repository']['full_name'],
            branch=data['pull_request']['head']['ref'],
            sha=data['pull_request']['head']['sha']
        )

    @staticmethod
    def get_tag_details(data: Dict) -> TagHookDetails:
        return TagHookDetails(
            repository=data['repository']['full_name'],
            tag=data['ref'][10:],
            sha=data['after']
        )

    @staticmethod
    def get_push_details(data: Dict) -> PushHookDetails:
        return PushHookDetails(
            repository=data['repository']['full_name'],
            branch=data['ref'][11:] if data['ref'].startswith('refs/heads/') else data['ref'],
            sha=data['after'],
            changes=HookDetailsFactory.__get_changes(data['commits'])
        )

    @staticmethod
    def __get_changes(commits: List[Dict]) -> Set[str]:
        additions = flatten_list([commit['added'] for commit in commits])
        removals = flatten_list([commit['removed'] for commit in commits])
        modifications = flatten_list([commit['modified'] for commit in commits])
        return set(additions + removals + modifications)

    @staticmethod
    def get_labeled_details(data) -> LabeledHookDetails:
        return LabeledHookDetails(
            repository=data['pull_request']['head']['repo']['full_name'],
            branch=data['pull_request']['head']['ref'],
            sha=data['pull_request']['head']['sha'],
            label=data['label']['name']
        )

    @staticmethod
    def get_pr_sync_details(data: Dict, head_branch: str, head_sha: str) -> PrOpenedHookDetails:
        return PrOpenedHookDetails(
            repository=data['repository']['full_name'],
            branch=head_branch,
            sha=head_sha
        )

    @staticmethod
    def get_release_details(data: Dict):
        return ReleaseHookDetails(
            repository=data['repository']['full_name'],
            tag=data['release']['tag_name'],
            release_target=data['release']['target_commitish'],
            is_prerelease=data['release']['prerelease']
        )
