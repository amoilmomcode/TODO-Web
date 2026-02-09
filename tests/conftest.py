"""pytest 설정 및 공통 fixture 정의."""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# 테스트용 인메모리 DB 사용
os.environ["DB_PATH"] = ":memory:"


@pytest_asyncio.fixture(scope="function")
async def client():
    """각 테스트마다 새로운 FastAPI TestClient 인스턴스를 생성한다."""
    import db.connection as db_conn
    from db import init_db, close_db

    # 매 테스트마다 DB 초기화
    db_conn._db = None

    from main import app

    # DB 초기화 (테이블 생성)
    await init_db()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    # 테스트 후 DB 연결 종료
    await close_db()


@pytest_asyncio.fixture
async def sample_category(client: AsyncClient) -> dict:
    """테스트용 샘플 카테고리를 생성한다."""
    response = await client.post(
        "/api/categories",
        json={"name": "업무"},
    )
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def sample_tags(client: AsyncClient) -> list[dict]:
    """테스트용 샘플 태그들을 생성한다."""
    tag1 = await client.post("/api/tags", json={"name": "긴급"})
    tag2 = await client.post("/api/tags", json={"name": "중요"})
    assert tag1.status_code == 201
    assert tag2.status_code == 201
    return [tag1.json(), tag2.json()]


@pytest_asyncio.fixture
async def sample_todo(client: AsyncClient) -> dict:
    """테스트용 샘플 TODO를 생성한다."""
    response = await client.post(
        "/api/todos",
        json={"title": "테스트 TODO"},
    )
    assert response.status_code == 201
    return response.json()
