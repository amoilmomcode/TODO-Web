"""FastAPI 앱 진입점."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI

from api.routes.todos import router as todos_router
from db import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """앱 시작 시 DB 초기화, 종료 시 연결 해제."""
    await init_db()
    yield
    await close_db()


app = FastAPI(title="TODO Web App", lifespan=lifespan)

app.include_router(todos_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
