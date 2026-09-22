from pydantic import BaseModel, Field
import sentry_sdk
from fastapi import FastAPI, HTTPException, Request

from api.common import init_sentry, require_authenticated_user, require_csrf
from config.settings import settings
from data.api_client import APIClient
from data.database import DatabaseManager

init_sentry()
app = FastAPI(docs_url=None, redoc_url=None)


class ApprovalRequest(BaseModel):
    suggestion_id: int = Field(gt=0)


@app.post("/")
async def approve_purchase(body: ApprovalRequest, request: Request):
    # The planned UI calls fetch(..., {credentials: 'include', headers:{'X-CSRF-Token': csrf}}).
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
