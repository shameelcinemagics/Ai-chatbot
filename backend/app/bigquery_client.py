from google.cloud import bigquery
from .config import settings


bq_client = bigquery.Client(project=settings.GOOGLE_PROJECT)




def run_query(sql: str, max_rows: int = 200):
    job = bq_client.query(sql)
    df = job.result().to_dataframe(create_bqstorage_client=False)
    if len(df) > max_rows:
            df = df.head(max_rows)
    return df