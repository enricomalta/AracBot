from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.common import enqueue_hourly_cycle, init_sentry, require_bearer
from config.settings import settings

init_sentry()
app = FastAPI(docs_url=None, redoc_url=None)


@app.post("/")
async def trigger(request: Request):
    require_bearer(request, settings.CRON_TRIGGER_SECRET)
    message_id = enqueue_hourly_cycle()
    return JSONResponse(status_code=202, content={"accepted": True, "message_id": message_id})


@app.get("/")
async def health():
    return {"ok": True}
