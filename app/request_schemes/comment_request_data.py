from typing import Dict
from collections import Counter


class CommentRequestData:
    repository = 'repository'
    sha = 'sha'
    body = 'body'
    job_name = 'jobName'

    @staticmethod
    def is_valid_comment_data(data: Dict) -> bool:
        return Counter([CommentRequestData.repository,
                        CommentRequestData.sha,
                        CommentRequestData.body,
                        CommentRequestData.job_name]) == Counter(data.keys())
