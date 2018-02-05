from app.clients.github_client import GithubClient
from app.enums.event_types import EventTypes
from app.exceptions.triggear_error import TriggearError
from app.mongo.labeled_document import LabeledDocument
from app.mongo.pr_opened_document import PrOpenedDocument
from app.mongo.push_document import PushDocument
from app.mongo.registration_cursor import RegistrationCursor
from app.mongo.release_document import ReleaseDocument
from app.mongo.tag_document import TagDocument
from app.mongo.triggerable_document import TriggerableDocument


class TriggerableDocumentFactory:
    @staticmethod
    def get_document(cursor: RegistrationCursor, github_client: GithubClient) -> TriggerableDocument:
        if cursor.event_type == EventTypes.labeled:
            return LabeledDocument(cursor, github_client)
        elif cursor.event_type == EventTypes.tagged:
            return TagDocument(cursor, github_client)
        elif cursor.event_type == EventTypes.pr_opened:
            return PrOpenedDocument(cursor, github_client)
        elif cursor.event_type == EventTypes.push:
            return PushDocument(cursor, github_client)
        elif cursor.event_type == EventTypes.release:
            return ReleaseDocument(cursor, github_client)
        raise TriggearError(f'No document type found for event type {event_type}')
