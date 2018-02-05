from typing import AsyncGenerator, Union

import motor.motor_asyncio
from datetime import datetime

from app.enums.event_types import EventType
from app.hook_details.hook_details import HookDetails
from app.mongo.registration_cursor import RegistrationCursor
from app.mongo.registration_fields import RegistrationFields
from app.mongo.registration_query import RegistrationQuery


class MongoClient:
    def __init__(self, mongo: motor.motor_asyncio.AsyncIOMotorClient):
        self.__mongo = mongo

    def get_registrations(self, event_type: EventType):
        return self.__mongo.registered[event_type.collection_name]

    async def get_registered_jobs(self, hook_details: HookDetails) -> AsyncGenerator[RegistrationCursor, None]:
        collection = self.__mongo.get_registrations(hook_details.get_event_type())
        async for cursor in collection.find(hook_details.get_query()):
            yield RegistrationCursor(hook_details.get_event_type(), cursor)

    async def increment_missed_counter(self, hook_details: HookDetails, registration_cursor: RegistrationCursor):
        collection = self.__mongo.get_registrations(hook_details.get_event_type())
        update_query = hook_details.get_query()
        update_query[RegistrationFields.JOB] = registration_cursor.job_name
        await collection.update_one(update_query, {'$inc': {RegistrationFields.MISSED_TIMES: 1}})

    def get_missed_jobs(self, event_type: EventType):
        return self.get_registrations(event_type).find({RegistrationFields.MISSED_TIMES: {'$gt': 0}})

    async def log_deregistration(self, caller: str, deregistration_query: RegistrationQuery):
        await self.__mongo.deregistered['log'].insert_one({'job': deregistration_query.job_name,
                                                           'caller': caller,
                                                           'eventType': deregistration_query.event_type,
                                                           'jenkins_url': deregistration_query.jenkins_url,
                                                           'timestamp': datetime.now()})
