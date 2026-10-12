"""Entry point: creates the FastAPI app, plugs in each group of endpoints, and maps errors to HTTP."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import health, instruments, portfolios, trades
from app.config import settings
from app.errors import ConflictError, NotFoundError, RulesViolated

app = FastAPI(title=settings.app_name)

# Every backend URL starts with /api so the frontend can tell them apart from pages.
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(portfolios.router, prefix="/api", tags=["portfolios"])
app.include_router(instruments.router, prefix="/api", tags=["instruments"])
app.include_router(trades.router, prefix="/api", tags=["trades"])


# ---- Error responses -----------------------------------------------------------------------
# Every validation problem uses one shape, so the frontend can show it next to the right field:
#   {"detail": "Validation failed", "errors": [{"field": "entry.price", "message": "..."}]}

@app.exception_handler(NotFoundError)
def handle_not_found(_: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
def handle_conflict(_: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(RulesViolated)
def handle_rules(_: Request, exc: RulesViolated):
    errors = [{"field": v.field, "message": v.message} for v in exc.violations]
    return JSONResponse(status_code=422, content={"detail": "Validation failed", "errors": errors})


@app.exception_handler(RequestValidationError)
def handle_request_validation(_: Request, exc: RequestValidationError):
    errors = [
        {
            # e.g. ("body", "entry", "price") -> "entry.price"
            "field": ".".join(str(part) for part in err["loc"] if part not in ("body", "query", "path")),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": "Validation failed", "errors": errors})
