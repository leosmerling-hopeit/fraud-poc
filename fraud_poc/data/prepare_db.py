# AUTOGENERATED! DO NOT EDIT! File to edit: 07-prepare-db.ipynb (unless otherwise specified).

__all__ = ['__steps__', 'logger']

# Cell
from typing import Dict
from datetime import datetime, timezone, timedelta
import random
import math
import dask.dataframe as dd
import numpy as np
import redis

from hopeit.server.serialization import serialize, Serialization, deserialize
from hopeit.server.compression import Compression
from hopeit.app.context import EventContext
from hopeit.app.events import Spawn, SHUFFLE
from hopeit.app.api import event_api
from hopeit.app.logger import app_logger
from hopeit.toolkit.storage.redis import RedisStorage

from ..jobs import get_client, FeatureCalcJob, PrepareDbJob

# Cell
__steps__ = ['update_database']

logger = app_logger()


# Cell
def _save_values_by_key(key, path, db_host, db_port):
    df = dd.read_parquet(path, engine='fastparquet')
    df['key'] = df[key]
    return (key, df.map_partitions(_foreach_partition, db_host, db_port, meta=('value', object)).count().compute().item())

def _foreach_partition(df, db_host, db_port):
    db = redis.Redis(host=db_host, port=db_port, db=0)
    items = df.groupby(['key'])[df.columns].apply(_last_item)
    items = items.apply(lambda x: _persist(x, db), axis=1)
    db.close()
    return items

def _last_item(group):
    group = group.sort_values('order_date')
    return group.tail(1)

def _persist(item, db):
    v = item.to_dict()
    key = v['key']
    payload = serialize(v, Serialization.PICKLE4, Compression.LZ4)
    db.set(key, payload)
    return v

# Cell
async def update_database(job: FeatureCalcJob, context: EventContext):
    client = get_client(context)
    db_host = context.env['db']['host']
    db_port = context.env['db']['port']
    logger.info(context, f"Preparing to save to database {db_host}:{db_port}...")
    try:
        tasks = []
        for key, path in job.features.items():
            logger.info(context, f"Saving latest state for {key} features...")
            tasks.append(client.submit(_save_values_by_key, key, path, db_host, db_port))
        res = client.gather(tasks)
        return PrepareDbJob(
            features=job.features,
            db=f'{db_host}:{db_port}',
            saved=dict(res)
        )
    except Exception as e:
        logger.error(context, e)
        return None
    finally:
        client.close()