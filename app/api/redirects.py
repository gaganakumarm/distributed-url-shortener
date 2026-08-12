from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.url import ShortURL
from app.models.click import ClickEvent
from app.services.cache import get_cached_url, set_cached_url

router = APIRouter(tags=["redirect"])


def truncate_header(value: str | None, max_length: int = 512) -> str | None:
    return value[:max_length] if value else None


@router.get("/{short_code}", include_in_schema=False)
async def redirect_short_url(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    cached = await get_cached_url(short_code)

    if cached:
        url_id, original_url = cached
    else:
        result = await db.execute(select(ShortURL).where(ShortURL.short_code == short_code))
        obj = result.scalar_one_or_none()

        if not obj:
            raise HTTPException(status_code=404, detail="Short URL not found")

        url_id = obj.id
        original_url = obj.original_url
        await set_cached_url(short_code, url_id, original_url)

    db.add(
        ClickEvent(
            url_id=url_id,
            referrer=truncate_header(request.headers.get("referer")),
            user_agent=truncate_header(request.headers.get("user-agent")),
        )
    )
    try:
        await db.commit()
    except SQLAlchemyError:
        # A stale cache entry or temporary analytics failure must not break a
        # redirect whose destination has already been resolved.
        await db.rollback()

    return RedirectResponse(url=original_url, status_code=307)
