# AUTOGENERATED! DO NOT EDIT! File to edit: 09-find-orders.ipynb (unless otherwise specified).

__all__ = ['__steps__', '__api__', 'logger', 'db', 'cur', 'scan_db']

# Cell
from typing import Dict, List
from datetime import datetime, timezone, timedelta
import os
import json
import pickle
import aioredis
from dataclasses import dataclass
from hopeit.dataobjects import dataobject
from hopeit.server.serialization import serialize, Serialization, deserialize
from hopeit.server.compression import Compression
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.app.api import event_api
from hopeit.app.logger import app_logger

from ..live.predict import OrderInfo

# Cell
__steps__ = ['scan_db']

__api__ = event_api(
    title="Test: Find Orders",
    query_args=[
        ("prefix", str, "Prefix for customer_id or email with * as a wildcard"),
        ("num_items", int, "Number of items to retrieve")
    ],
    responses={
        200: (List[OrderInfo], "list of orders")
    }
)

logger = app_logger()

db = None
cur = b'0'


# Cell
async def scan_db(payload: None, context: EventContext, prefix: str, num_items: int):
    address = context.env['db']['url']
    logger.info(context, f"Connecting to database {address}...")
    results = []
    redis = await aioredis.create_redis(address)
    cur = b'0'  # set initial cursor to 0
    for i in range(int(num_items)):
        cur, keys = await redis.scan(cur, match=f'{prefix}*')
        if cur is None: break
    print(keys)
    for k in keys:
        try:
            item = await redis.get(k)
            item = deserialize(item, Serialization.PICKLE4, Compression.LZ4, dict)
            results.append(OrderInfo.from_dict({'location_lat': 0.0, 'location_long': 0.0, **item}))
        except Exception as e:
            pass # Ignoring items that are not orders, this is just a test method
    return results