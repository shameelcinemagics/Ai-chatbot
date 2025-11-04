from google.cloud import bigquery
from .config import get_settings

settings = get_settings()
_bq = bigquery.Client(project=settings.GCP_PROJECT)

_schema_cache: str | None = None

async def get_schema_ddl() -> str:
    global _schema_cache
    if _schema_cache:
        return _schema_cache
    tables = list(_bq.list_tables(settings.BQ_DATASET))
    parts = []
    for t in tables:
        table = _bq.get_table(t)
        cols = []
        for f in table.schema:
            suffix = "[]" if f.mode == "REPEATED" else ""
            cols.append(f"{f.name} {f.field_type}{suffix}")
        parts.append(f"TABLE {t.dataset_id}.{t.table_id} ( {', '.join(cols)} )")
    _schema_cache = "\n".join(parts)
    return _schema_cache

def sql_guard(sql: str) -> str:
    s = " ".join(sql.strip().split())
    import re
    if ";" in s:
        raise ValueError("Multiple statements not allowed")
    if re.search(r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE)\b", s, re.I):
        raise ValueError("Only SELECT queries are allowed")
    if not re.match(r"^SELECT\b", s, re.I):
        raise ValueError("Query must start with SELECT")
    if not re.search(r"\bLIMIT\s+\d+\b", s, re.I):
        s += " LIMIT 1000"
    else:
        s = re.sub(r"\bLIMIT\s+(\d+)\b", lambda m: f"LIMIT {min(int(m.group(1)), 5000)}", s, flags=re.I)
    return s

def dry_run(sql: str) -> None:
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    _bq.query(sql, job_config=job_config)

def run_query(sql: str) -> list[dict]:
    job = _bq.query(sql)
    rows = [dict(r) for r in job.result()]
    return rows
