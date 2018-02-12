from typing import List

import pytest
from datetime import datetime
from mockito import mock, expect, captor
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorCursor
from pymongo.results import InsertOneResult, UpdateResult

from app.clients.mongo_client import MongoClient
from app.enums.event_types import EventType
from app.hook_details.hook_details import HookDetails
from app.mongo.clear_query import ClearQuery
from app.mongo.deregistration_query import DeregistrationQuery
from app.mongo.registration_cursor import RegistrationCursor
from app.mongo.registration_query import RegistrationQuery
from tests.async_mockito import async_iter, async_value

pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures('unstub')
class TestMongoClient:
    async def test__get_registration(self):
        collection: AsyncIOMotorCollection = mock(spec=AsyncIOMotorCollection, strict=True)
        mongo: AsyncIOMotorClient = mock({'registered': {'push': collection}}, spec=AsyncIOMotorClient, strict=True)
        assert MongoClient(mongo).get_registrations(EventType.PUSH) == collection

    async def test__get_registered_jobs(self):
        cursor: AsyncIOMotorCursor = mock(spec=AsyncIOMotorCursor, strict=True)
        collection: AsyncIOMotorCollection = mock(spec=AsyncIOMotorCollection, strict=True)
        mongo: AsyncIOMotorClient = mock(spec=AsyncIOMotorClient, strict=True)
        hook_details: HookDetails = mock(spec=HookDetails, strict=True)

        mongo_client = MongoClient(mongo)
        expect(hook_details).get_event_type().thenReturn(EventType.RELEASE)
        expect(hook_details).get_query().thenReturn({})
        expect(mongo_client).get_registrations(EventType.RELEASE).thenReturn(collection)
        expect(collection).find({}).thenReturn(async_iter(cursor, cursor))

        async for job in mongo_client.get_registered_jobs(hook_details):
            assert job.cursor == cursor

    async def test__increment_missed_counter(self):
        collection: AsyncIOMotorCollection = mock(spec=AsyncIOMotorCollection, strict=True)
        mongo: AsyncIOMotorClient = mock(spec=AsyncIOMotorClient, strict=True)
        hook_details: HookDetails = mock(spec=HookDetails, strict=True)
        registration_cursor: RegistrationCursor = mock({'job_name': 'job'}, spec=RegistrationCursor, strict=True)

        mongo_client = MongoClient(mongo)
        expect(hook_details).get_event_type().thenReturn(EventType.RELEASE)
        expect(hook_details).get_query().thenReturn({})
        expect(mongo_client).get_registrations(EventType.RELEASE).thenReturn(collection)
        expect(collection).update_one({'job': 'job'}, {'$inc': {'missed_times': 1}}).thenReturn(async_value(None))

        await mongo_client.increment_missed_counter(hook_details, registration_cursor)

    async def test__get_missed_jobs(self):
        missed_jobs: AsyncIOMotorCursor = mock(spec=AsyncIOMotorCursor, strict=True)
        collection: AsyncIOMotorCollection = mock(spec=AsyncIOMotorCollection, strict=True)
        mongo: AsyncIOMotorClient = mock(spec=AsyncIOMotorClient, strict=True)
        mongo_client = MongoClient(mongo)
        expect(mongo_client).get_registrations(EventType.TAGGED).thenReturn(collection)
        expect(collection).find({'missed_times': {'$gt': 0}}).thenReturn(async_value(missed_jobs))
        assert await mongo_client.get_missed_jobs(EventType.TAGGED) == missed_jobs

    async def test__log_deregistration(self):
        collection: AsyncIOMotorCollection = mock(spec=AsyncIOMotorCollection, strict=True)
        mongo: AsyncIOMotorClient = mock({'deregistered': {'log': collection}}, spec=AsyncIOMotorClient, strict=True)
        deregistration_query: DeregistrationQuery = mock({'job_name': 'job', 'caller': 'me', 'event_type': 'type', 'jenkins_url': 'url'},
                                                         spec=DeregistrationQuery, strict=True)
        mongo_client = MongoClient(mongo)

        arg_captor = captor()
        expect(collection).insert_one(arg_captor).thenReturn(async_value(None))
        await mongo_client.log_deregistration(deregistration_query)
        assert isinstance(arg_captor.value, dict)
        assert arg_captor.value['job'] == 'job'
        assert arg_captor.value['caller'] == 'me'
        assert arg_captor.value['eventType'] == 'type'
        assert arg_captor.value['jenkins_url'] == 'url'
        assert isinstance(arg_captor.value['timestamp'], datetime)

    async def test__deregister(self):
        mock(EventType)
        collection: AsyncIOMotorCollection = mock(spec=AsyncIOMotorCollection, strict=True)
        mongo: AsyncIOMotorClient = mock({'deregistered': {'log': collection}}, spec=AsyncIOMotorClient, strict=True)
        deregistration_query: DeregistrationQuery = mock({'job_name': 'job', 'caller': 'me', 'event_type': 'push', 'jenkins_url': 'url'},
                                                         spec=DeregistrationQuery, strict=True)
        mongo_client = MongoClient(mongo)
        expect(EventType).get_by_collection_name(name='push').thenReturn(EventType.PUSH)
        expect(mongo_client).get_registrations(EventType.PUSH).thenReturn(collection)
        expect(deregistration_query).get_deregistration_query().thenReturn({})
        expect(collection).delete_one({}).thenReturn(async_value(None))
        expect(mongo_client).log_deregistration(deregistration_query=deregistration_query).thenReturn(async_value(None))
        await mongo_client.deregister(deregistration_query)

    async def test__clear(self):
        collection: AsyncIOMotorCollection = mock(spec=AsyncIOMotorCollection, strict=True)
        mongo: AsyncIOMotorClient = mock(spec=AsyncIOMotorClient, strict=True)
        clear_query: ClearQuery = mock({'event_type': 'push'}, spec=ClearQuery, strict=True)
        mongo_client = MongoClient(mongo)

        expect(EventType).get_by_collection_name(name='push').thenReturn(EventType.PUSH)
        expect(mongo_client).get_registrations(EventType.PUSH).thenReturn(collection)
        expect(clear_query).get_clear_query().thenReturn({})
        expect(collection).update_one({}, {'$set': {'missed_times': 0}}).thenReturn(async_value(None))
        await mongo_client.clear(clear_query)

    async def test__get_missed_info(self):
        mongo: AsyncIOMotorClient = mock(spec=AsyncIOMotorClient, strict=True)
        mongo_client = MongoClient(mongo)

        first_doc = {'jenkins_url': 'url1', 'job': 'job1', 'missed_times': 2}
        second_doc = {'jenkins_url': 'url2', 'job': 'job2', 'missed_times': 22}
        expect(mongo_client).get_missed_jobs(EventType.PUSH).thenReturn(async_iter(first_doc, second_doc))
        result: List[str] = await mongo_client.get_missed_info('push')
        assert len(result) == 2
        assert 'url1:job1#2' in result
        assert 'url2:job2#22' in result

    async def test__add_or_update__should_add__if_registration_does_not_exist(self):
        collection: AsyncIOMotorCollection = mock(spec=AsyncIOMotorCollection, strict=True)
        mongo: AsyncIOMotorClient = mock(spec=AsyncIOMotorClient, strict=True)
        mongo_client = MongoClient(mongo)
        registration_query: RegistrationQuery = mock({'event_type': 'push'}, spec=RegistrationQuery, strict=True)
        insertion_result: InsertOneResult = mock({'inserted_id': 23}, spec=InsertOneResult, strict=True)

        expect(registration_query).get_registration_query().thenReturn({})
        expect(mongo_client).get_registrations(EventType.PUSH).thenReturn(collection)
        expect(collection).find_one({}).thenReturn(async_value(None))
        expect(registration_query).get_full_document().thenReturn({'new': 'document'})
        expect(collection).insert_one({'new': 'document'}).thenReturn(async_value(insertion_result))
        await mongo_client.add_or_update_registration(registration_query)

    async def test__add_or_update__should_update__if_registration_exists(self):
        cursor: AsyncIOMotorCursor = mock(spec=AsyncIOMotorCursor, strict=True)
        collection: AsyncIOMotorCollection = mock(spec=AsyncIOMotorCollection, strict=True)
        mongo: AsyncIOMotorClient = mock(spec=AsyncIOMotorClient, strict=True)
        mongo_client = MongoClient(mongo)
        registration_query: RegistrationQuery = mock({'event_type': 'push'}, spec=RegistrationQuery, strict=True)
        update_result: UpdateResult = mock({'matched_count': 1}, spec=UpdateResult, strict=True)

        expect(registration_query).get_registration_query().thenReturn({})
        expect(mongo_client).get_registrations(EventType.PUSH).thenReturn(collection)
        expect(collection).find_one({}).thenReturn(async_value(cursor))
        expect(registration_query).get_full_document().thenReturn({'new': 'document'})
        expect(collection).replace_one(cursor, {'new': 'document'}).thenReturn(async_value(update_result))
        await mongo_client.add_or_update_registration(registration_query)


