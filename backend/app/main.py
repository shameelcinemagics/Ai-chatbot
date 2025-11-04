from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from .config import get_settings
from .auth import router as auth_router
from .schemas import AskRequest, AskResponse
from .bigquery_client import get_schema_ddl, sql_guard, dry_run, run_query
from .vertex_client import gen_text, sql_system_prompt, summary_system_prompt
from .auth import require_user

settings = get_settings()

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"ok": True}

app.include_router(auth_router)

@app.post("/bot/ask", response_model=AskResponse)
def ask(req: AskRequest, user_id: str = Depends(require_user)):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question required")

    schema = app.state.schema if hasattr(app.state, "schema") else None
    if not schema:
        # Cache schema at first request
        schema = app.state.schema = __import__("asyncio").get_event_loop().run_until_complete(get_schema_ddl())

    # 1) NL -> SQL (Vertex)
    system = sql_system_prompt(schema)
    sql = gen_text(
        parts=[
            {"role": "system", "parts": [{"text": system}]},
            {"role": "user", "parts": [{"text": req.question}]},
        ],
        temperature=0.2,
        max_tokens=512,
    )
    sql = sql_guard(sql)

    # 2) Dry run for safety/cost
    dry_run(sql)

    # 3) Run and summarize
    rows = run_query(sql)
    summary = gen_text(
        parts=[
            {"role": "system", "parts": [{"text": summary_system_prompt()}]},
            {"role": "user", "parts": [{"text": __import__('json').dumps({"question": req.question, "rows": rows[:50]})}]},
        ],
        temperature=0.3,
        max_tokens=256,
    )
    return AskResponse(sql=sql, rows=rows, summary=summary)
