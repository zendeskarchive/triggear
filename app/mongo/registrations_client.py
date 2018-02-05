from typing import AsyncGenerator

import motor.motor_asyncio

from app.enums.registration_fields import RegistrationFields
from app.hook_details.hook_details import HookDetails
from app.mongo.registration_cursor import RegistrationCursor


class RegistrationsClient:
    def __init__(self, mongo_client: motor.motor_asyncio.AsyncIOMotorClient):
        self.__mongo_client = mongo_client

    def __get_collection_for_event_type(self, event_type: str):
        return self.__mongo_client.registered[event_type]

    async def get_registered_jobs(self, hook_details: HookDetails) -> AsyncGenerator[RegistrationCursor, None]:
        collection = self.__get_collection_for_event_type(hook_details.get_event_type())
        async for cursor in collection.find(hook_details.get_query()):
            yield RegistrationCursor(hook_details.get_event_type(), cursor)

    async def increment_missed_counter(self, hook_details: HookDetails, registration_cursor: RegistrationCursor):
        collection = self.__get_collection_for_event_type(hook_details.get_event_type())
        update_query = hook_details.get_query()
        update_query[RegistrationFields.job] = registration_cursor.job_name
        await collection.update_one(update_query, {'$inc': {RegistrationFields.missed_times: 1}})
