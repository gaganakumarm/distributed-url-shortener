from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.api import auth, urls, redirects, health
from app.core.middleware import operational_middleware


app = FastAPI(title=settings.app_name)


app.middleware("http")(operational_middleware)
app.mount("/metrics", make_asgi_app())

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(urls.router)
app.include_router(redirects.router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/health/ready",
    }
