from fastapi import FastAPI
from .routers import health, chat
from .routers import reindex as reindex_router

app = FastAPI(title="FAQ Bot API", version="0.1.0")
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(chat.router, tags=["chat"])
app.include_router(reindex_router.router, tags=["admin"])
