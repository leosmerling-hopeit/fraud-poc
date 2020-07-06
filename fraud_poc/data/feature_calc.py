# AUTOGENERATED! DO NOT EDIT! File to edit: 03-feature-calc.ipynb (unless otherwise specified).

__all__ = ['__steps__', 'logger', 'calculate', 'count_distinct_values', 'num_stats', 'run']

# Cell
import dask.dataframe as dd
import numpy as np

from hopeit.app.context import EventContext
from hopeit.app.events import Spawn, SHUFFLE
from hopeit.app.api import event_api
from hopeit.app.logger import app_logger

from ..jobs import get_client, FeatureCalcJob, PreprocessingJob

# Cell
__steps__ = ['run']

logger = app_logger()

# Cell
def calculate(df, count_cols, stat_cols, by):
    counts = count_distinct_values(df, count_cols, by)
    stats = num_stats(df, stat_cols, by)
    right = counts.merge(stats)
    df = df.merge(right,
                  left_on=[df.index, 'order_id'],
                  right_on=[by, 'order_id'],
                  suffixes=('', f's_by_{by}'))
    return df


def count_distinct_values(df, cols, by):
    results = []
    for col in cols:
        results.append(
            df.groupby([df.index, df.order_date, df.order_id])[col] \
                .apply(list) \
                .sort_index() \
                .groupby(level=0) \
                .apply(np.cumsum) \
                .apply(lambda x: len(set(x))))

    counts = results[0].to_frame()
    for col, result in zip(cols[1:], results[1:]):
        counts[col] = result

    counts = counts.reset_index()[[by, 'order_id', *cols]]
    return counts

def num_stats(df, cols, by):
    results = []
    for col in cols:
        results.append(df.groupby([df.index, df.order_date, df.order_id])[col] \
                .apply(list) \
                .sort_index() \
                .groupby(level=0) \
                .apply(np.cumsum) \
                .apply(lambda x: (np.mean(x), np.std(x), np.min(x), np.max(x), np.sum(x))))

    stats = results[0].to_frame()
    for col, result in zip(cols[1:], results[1:]):
        stats[col] = result

    stats = stats.reset_index()[[by, 'order_id', *cols]]
    for col in cols:
        stats[f'{col}_mean_by_{by}'] = stats[col].apply(lambda x: x[0])
        stats[f'{col}_std_by_{by}'] = stats[col].apply(lambda x: x[1])
        stats[f'{col}_min_by_{by}'] = stats[col].apply(lambda x: x[2])
        stats[f'{col}_max_by_{by}'] = stats[col].apply(lambda x: x[3])
        stats[f'{col}_sum_by_{by}'] = stats[col].apply(lambda x: x[4])
        stats[col] = stats[col].apply(str)

    return stats


# Cell
def run(job: PreprocessingJob, context: EventContext) -> FeatureCalcJob:
    base_path = context.env['data']['features']
    client = get_client(context)
    features = {}
    try:
        path = job.partitioned.get('customer_id')
        if path:
            logger.info(context, "Calculating features on customer_id...")
            df = dd.read_parquet(path,
                         engine='fastparquet',
                         columns=['order_id', 'order_date', 'email', 'ip_addr', 'order_amount'])
            df = df.map_partitions(calculate, count_cols=['email', 'ip_addr'], stat_cols=['order_amount'], by='customer_id')
            save_path = f'{base_path}/customer_id/'
            df.to_parquet(save_path)
            features['customer_id'] = save_path
            logger.info(context, f"Saved {save_path}.")

        path = job.partitioned.get('email')
        if path:
            logger.info(context, "Calculating features on email...")
            df = dd.read_parquet(path,
                         engine='fastparquet',
                         columns=['order_id', 'order_date', 'customer_id', 'ip_addr', 'order_amount'])
            df = df.map_partitions(calculate, count_cols=['customer_id'], stat_cols=['order_amount'], by='email')
            save_path = f'{base_path}/email/'
            df.to_parquet(save_path)
            features['email'] = save_path
            logger.info(context, f"Saved {save_path}.")

        return FeatureCalcJob(
            sources=job.partitioned,
            features=features
        )
    except Exception as e:
        logger.error(context, e)
        return None
    finally:
        client.close()