"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI

from retailernews.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="Retailer News", description="Retail insights crawler API")
    app.include_router(router, prefix="/api")
    return app


app = create_app()
