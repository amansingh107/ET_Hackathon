from fastapi import APIRouter
from sqlalchemy import text
from app.database import engine
import redis as redis_client
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Check if the API and all dependencies are reachable."""
    status = {"api": "ok", "database": "error", "redis": "error"}

    # Check PostgreSQL
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["database"] = "ok"
    except Exception as e:
        status["database"] = f"error: {str(e)}"

    # Check Redis
    try:
        r = redis_client.from_url(settings.redis_url)
        r.ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"

    overall = "ok" if all(v == "ok" for v in status.values()) else "degraded"
    return {"status": overall, "services": status}
