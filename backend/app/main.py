from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.app.api import applications, auth, executions, monitoring, workflows

ROOT = Path(__file__).parent
app = FastAPI(
    title="SailPoint RPA Studio",
    version="0.1.0",
    description="Phase 1 — web RPA orchestration. SailPoint adapter is planned for phase 3.",
)
for router in (
    auth.router,
    applications.router,
    workflows.router,
    executions.router,
    monitoring.router,
):
    app.include_router(router)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    # Validate body size including chunked requests before Pydantic parses the payload.
    if request.method in {"POST", "PUT", "PATCH"}:
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > 1_000_000:
                return JSONResponse({"detail": "Payload muito grande"}, status_code=413)
        request._body = bytes(data)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    if request.url.path not in {"/docs", "/redoc", "/docs/oauth2-redirect"}:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        )
    return response


@app.get("/", include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse({"detail": errors}, status_code=422)
