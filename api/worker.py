import json

import sentry_sdk
from fastapi import FastAPI, Request

from api.common import init_sentry, verify_qstash
from data.database import DatabaseManager
from main import AdvancedBitcoinPatternTracker

init_sentry()
app = FastAPI(docs_url=None, redoc_url=None)


@app.post("/")
async def worker(request: Request):
    raw_body = await request.body()
    verify_qstash(request, raw_body)
    payload = json.loads(raw_body or b"{}")
    db = DatabaseManager()
    run_id = db.create_analysis_run(request.headers.get("upstash-message-id"))
    try:
        summary = AdvancedBitcoinPatternTracker().run_serverless_cycle()
        db.finish_analysis_run(run_id, "completed", summary=summary)
        return {"ok": True, "run_id": run_id, "summary": summary}
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        db.finish_analysis_run(run_id, "failed", error=str(exc), summary={"payload": payload})
        raise
