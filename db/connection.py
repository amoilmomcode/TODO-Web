"""SQLite 데이터베이스 연결 관리 모듈."""

import os
from pathlib import Path

import aiosqlite
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 기준 DB 파일 경로
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "todo.db")))
INIT_SQL_PATH = Path(__file__).resolve().parent / "init.sql"

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """현재 DB 연결을 반환한다. 없으면 새로 생성한다."""
    global _db
    if _db is None:
        # DB 파일이 위치할 디렉토리가 없으면 생성
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(DB_PATH))
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA foreign_keys = ON")
    return _db


async def init_db() -> None:
    """init.sql 스크립트를 실행하여 테이블을 초기화한다."""
    db = await get_db()
    sql = INIT_SQL_PATH.read_text(encoding="utf-8")
    await db.executescript(sql)
    await db.commit()


async def close_db() -> None:
    """DB 연결을 종료한다."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
