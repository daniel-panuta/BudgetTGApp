from fastapi import FastAPI

from .api.routers.health import router as health_router
from .api.routers.transactions import router as transactions_router
from .core.config import API_NAME, API_VERSION
from .core.logging import configure_logging

configure_logging()

app = FastAPI(title=API_NAME, version=API_VERSION)

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(transactions_router, prefix="/api/v1/transactions", tags=["transactions"])