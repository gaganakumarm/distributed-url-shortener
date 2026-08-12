from datetime import datetime
from pydantic import BaseModel, AnyHttpUrl


class URLCreate(BaseModel):
    url: AnyHttpUrl


class URLResponse(BaseModel):
    id: int
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime


class URLStats(BaseModel):
    short_code: str
    total_clicks: int
