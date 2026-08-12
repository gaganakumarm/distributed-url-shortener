from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.url import ShortURL
from app.models.click import ClickEvent
from app.schemas.url import URLCreate, URLResponse, URLStats
from app.services.shortcodes import generate_short_code
from app.services.cache import set_cached_url, delete_cached_url

router = APIRouter(prefix="/api/urls", tags=["urls"])


def serialize_url(obj: ShortURL) -> URLResponse:
    return URLResponse(
        id=obj.id,
        short_code=obj.short_code,
        short_url=f"{settings.base_url}/{obj.short_code}",
        original_url=obj.original_url,
        created_at=obj.created_at,
    )


@router.post("", response_model=URLResponse, status_code=201)
async def create_url(
    payload: URLCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    owner_id = current_user.id
    obj = None
    for _ in range(10):
        code = generate_short_code(settings.short_code_length)
        candidate = ShortURL(
            short_code=code,
            original_url=str(payload.url),
            owner_id=owner_id,
        )
        db.add(candidate)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue
        obj = candidate
        break

    if obj is None:
        raise HTTPException(status_code=503, detail="Could not generate unique short code")

    await db.refresh(obj)
    await set_cached_url(obj.short_code, obj.id, obj.original_url)
    return serialize_url(obj)


@router.get("", response_model=list[URLResponse])
async def list_urls(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ShortURL)
        .where(ShortURL.owner_id == current_user.id)
        .order_by(ShortURL.created_at.desc())
    )
    return [serialize_url(item) for item in result.scalars().all()]


@router.get("/{short_code}/stats", response_model=URLStats)
async def stats(
    short_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ShortURL).where(
            ShortURL.short_code == short_code,
            ShortURL.owner_id == current_user.id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="URL not found")

    count_result = await db.execute(
        select(func.count(ClickEvent.id)).where(ClickEvent.url_id == obj.id)
    )
    return URLStats(short_code=short_code, total_clicks=count_result.scalar_one())


@router.delete("/{short_code}", status_code=204)
async def delete_url(
    short_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ShortURL).where(
            ShortURL.short_code == short_code,
            ShortURL.owner_id == current_user.id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="URL not found")

    await db.delete(obj)
    await db.commit()
    await delete_cached_url(short_code)
