from .config import settings
from google.cloud import aiplatform


aiplatform.init(project=settings.GOOGLE_PROJECT, location=settings.VERTEX_LOCATION)


MODEL = settings.VERTEX_MODEL




def generate_sql(natural_query: str, table_schema: str) -> str:
    prompt = f"""
    You are an expert BigQuery SQL generator. Produce a single valid SQL SELECT statement (no modifying statements) that answers the user's question. Use only the schema below:


    {table_schema}


    User question:
    {natural_query}


    Return only the SQL statement, nothing else.
    """
    model = aiplatform.TextGenerationModel.from_pretrained(MODEL)
    resp = model.predict(prompt, max_output_tokens=512, temperature=0.0)
    return resp.text.strip()




def summarize_dataframe(df) -> str:
    sample = df.head(20).to_csv(index=False)
    prompt = f"Summarize the following query results in 2-3 sentences:\n\n{sample}"
    model = aiplatform.TextGenerationModel.from_pretrained(MODEL)
    resp = model.predict(prompt, max_output_tokens=256, temperature=0.2)
    return resp.text.strip()