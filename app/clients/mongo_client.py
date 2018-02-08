import logging
from typing import AsyncGenerator, Union, List, AsyncIterable

import motor.motor_asyncio
from datetime import datetime

from app.enums.event_types import EventType
from app.hook_details.hook_details import HookDetails
from app.mongo.clear_query import ClearQuery
from app.mongo.deregistration_query import DeregistrationQuery
from app.mongo.registration_cursor import RegistrationCursor
from app.mongo.registration_fields import RegistrationFields
from app.mongo.registration_query import RegistrationQuery


class MongoClient:
    def __init__(self, mongo: motor.motor_asyncio.AsyncIOMotorClient) -> None:
        self.__mongo = mongo

    def get_registrations(self, event_type: EventType) -> motor.motor_asyncio.AsyncIOMotorCollection:
        return self.__mongo.registered[event_type.collection_name]

    async def get_registered_jobs(self, hook_details: HookDetails) -> AsyncGenerator[RegistrationCursor, None]:
        collection = self.__mongo.get_registrations(hook_details.get_event_type())
        async for cursor in collection.find(hook_details.get_query()):
            yield RegistrationCursor(cursor)

    async def increment_missed_counter(self, hook_details: HookDetails, registration_cursor: RegistrationCursor) -> None:
        collection = self.__mongo.get_registrations(hook_details.get_event_type())
        update_query = hook_details.get_query()
        update_query[RegistrationFields.JOB] = registration_cursor.job_name
        await collection.update_one(update_query, {'$inc': {RegistrationFields.MISSED_TIMES: 1}})

    def get_missed_jobs(self, event_type: EventType) -> motor.motor_asyncio.AsyncIOMotorCursor:
        return self.get_registrations(event_type).find({RegistrationFields.MISSED_TIMES: {'$gt': 0}})

    async def log_deregistration(self, deregistration_query: DeregistrationQuery) -> None:
        await self.__mongo.deregistered['log'].insert_one({'job': deregistration_query.job_name,
                                                           'caller': deregistration_query.caller,
                                                           'eventType': deregistration_query.event_type,
                                                           'jenkins_url': deregistration_query.jenkins_url,
                                                           'timestamp': datetime.now()})

    async def deregister(self, deregistration_query: DeregistrationQuery) -> None:
        collection = self.get_registrations(EventType.get_by_collection_name(name=deregistration_query.event_type))
        await collection.delete_one(deregistration_query.get_deregistration_query())
        await self.log_deregistration(deregistration_query=deregistration_query)

    async def clear(self, clear_query: ClearQuery) -> None:
        collection = self.get_registrations(EventType.get_by_collection_name(name=clear_query.event_type))
        await collection.update_one(clear_query.get_clear_query(), {'$set': {RegistrationFields.MISSED_TIMES: 0}})

    async def get_missed_info(self, event_type: str) -> List[str]:
        return [f'{document[RegistrationFields.JENKINS_URL]}:{document[RegistrationFields.JOB]}#{document[RegistrationFields.MISSED_TIMES]}'
                async for document in self.get_missed_jobs(EventType.get_by_collection_name(name=event_type))]

    async def add_or_update_registration(self, registration_query: RegistrationQuery) -> None:
        collection = self.get_registrations(EventType.get_by_collection_name(name=registration_query.event_type))
        found_doc = await collection.find_one(registration_query.get_registration_query())
        if not found_doc:
            result = await collection.insert_one(registration_query.get_full_document())
            logging.info(f"Inserted document with ID {repr(result.inserted_id)}")
        else:
            result = await collection.replace_one(found_doc, registration_query.get_full_document())
            logging.info(f"Updated {repr(result.matched_count)} documents")
