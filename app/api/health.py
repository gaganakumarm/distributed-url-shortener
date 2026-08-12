from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.cache import redis_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live():
    return {"status": "ok"}


@router.get("/ready")
async def ready(response: Response, db: AsyncSession = Depends(get_db)):
    db_ok = True
    redis_ok = True

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    try:
        await redis_client.ping()
    except Exception:
        redis_ok = False

    if not db_ok:
        response.status_code = 503

    return {
        "status": "ready" if db_ok and redis_ok else ("degraded" if db_ok else "not_ready"),
        "postgres": db_ok,
        "redis": redis_ok,
    }
