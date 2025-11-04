from typing import Any
from .config import get_settings

# Using google-cloud-aiplatform's vertexai SDK (ADC auth recommended)
from vertexai import init as vertex_init
from vertexai.generative_models import GenerativeModel, GenerationConfig

settings = get_settings()

vertex_init(project=settings.GCP_PROJECT, location=settings.VERTEX_REGION)
_model = GenerativeModel(settings.VERTEX_MODEL)

def gen_text(parts: list[dict[str, Any]], temperature: float = 0.2, max_tokens: int = 512) -> str:
    cfg = GenerationConfig(temperature=temperature, max_output_tokens=max_tokens)
    resp = _model.generate_content(contents=parts, generation_config=cfg)
    return (resp.candidates[0].content.parts[0].text if resp.candidates and resp.candidates[0].content.parts else "").strip()

def sql_system_prompt(schema: str) -> str:
    return f"""You are an expert BigQuery analyst.
Output ONE BigQuery Standard SQL SELECT only. No code fences, no commentary.
Use ONLY the following dataset/tables/columns:
{schema}

- Prefer {settings.BQ_DATASET}.{settings.BQ_DEFAULT_TABLE} unless user asks otherwise.
- Apply reasonable date filters when implied.
- Include LIMIT if missing."""

def summary_system_prompt() -> str:
    return "Summarize the JSON rows for a business stakeholder in 2–5 sentences, avoiding SQL jargon."
