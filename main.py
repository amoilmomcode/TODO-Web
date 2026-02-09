"""FastAPI 앱 진입점."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes.categories import router as categories_router
from api.routes.tags import router as tags_router
from api.routes.todos import router as todos_router
from db import close_db, init_db

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """앱 시작 시 DB 초기화, 종료 시 연결 해제."""
    await init_db()
    yield
    await close_db()


app = FastAPI(title="TODO Web App", lifespan=lifespan)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(todos_router)
app.include_router(categories_router)
app.include_router(tags_router)

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/")
async def root() -> FileResponse:
    """루트 경로에서 index.html을 서빙한다."""
    return FileResponse(str(BASE_DIR / "static" / "index.html"))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
