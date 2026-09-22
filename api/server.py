"""Single FastAPI entrypoint required by Vercel's current Python runtime."""
import json

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.common import (
    enqueue_hourly_cycle,
    init_sentry,
    require_authenticated_user,
    require_bearer,
    require_csrf,
    verify_qstash,
)
from config.settings import settings
from data.api_client import APIClient
from data.database import DatabaseManager
from main import AdvancedBitcoinPatternTracker

init_sentry()
app = FastAPI(docs_url=None, redoc_url=None)


class ApprovalRequest(BaseModel):
    suggestion_id: int = Field(gt=0)


@app.get("/api/cron")
async def cron_health():
    return {"ok": True}


@app.post("/api/cron")
async def trigger_cron(request: Request):
    require_bearer(request, settings.CRON_TRIGGER_SECRET)
    message_id = enqueue_hourly_cycle()
    return JSONResponse(status_code=202, content={"accepted": True, "message_id": message_id})


@app.post("/api/worker")
async def run_worker(request: Request):
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


@app.post("/api/approve-purchase")
async def approve_purchase(body: ApprovalRequest, request: Request):
    # UI: fetch(..., {credentials:'include', headers:{'X-CSRF-Token': csrf}})
    require_csrf(request)
    user = require_authenticated_user(request)
    if not settings.ENABLE_LIVE_TRADING:
        raise HTTPException(status_code=409, detail="Live trading is disabled")
    db = DatabaseManager()
    suggestion = db.claim_purchase_suggestion(body.suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=409, detail="Suggestion is unavailable, expired, or already being processed")
    try:
        order = APIClient(db).place_market_order(suggestion["symbol"], "BUY", float(suggestion["quantity"]))
        if not order or "orderId" not in order:
            raise RuntimeError("Binance did not accept the market buy order")
        position_id = db.open_position(suggestion, str(order["orderId"]), user["id"])
        return {"approved": True, "position_id": position_id, "order_id": str(order["orderId"])}
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        db.release_purchase_suggestion(body.suggestion_id, str(exc))
        raise HTTPException(status_code=502, detail="Purchase could not be executed; the suggestion was released")
