from fastapi import APIRouter
from app.api.v1 import health
from app.api.v1 import stocks, ingest, signals, patterns

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(stocks.router)
api_router.include_router(ingest.router)
api_router.include_router(signals.router)
api_router.include_router(patterns.router)
