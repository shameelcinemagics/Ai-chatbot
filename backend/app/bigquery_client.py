from functools import lru_cache
from typing import Any

from google.cloud import bigquery

from .config import get_settings


@lru_cache
def _get_bigquery_client() -> bigquery.Client:
    settings = get_settings()
    return bigquery.Client(project=settings.GCP_PROJECT)


def run_query(sql: str, max_rows: int = 200) -> Any:
    client = _get_bigquery_client()
    job = client.query(sql)
    df = job.result().to_dataframe(create_bqstorage_client=False)
    if len(df) > max_rows:
        df = df.head(max_rows)
    return df
