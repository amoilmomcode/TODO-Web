"""카테고리 CRUD API 통합 테스트."""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# 카테고리 생성 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_category(client: AsyncClient):
    """카테고리 생성이 정상 동작하는지 확인한다."""
    response = await client.post(
        "/api/categories",
        json={"name": "업무"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "업무"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_category_duplicate(client: AsyncClient):
    """중복된 카테고리 이름으로 생성 시 409 에러가 발생하는지 확인한다."""
    await client.post("/api/categories", json={"name": "업무"})

    response = await client.post("/api/categories", json={"name": "업무"})
    assert response.status_code == 409
    assert "이미 존재하는 카테고리입니다" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_category_empty_name(client: AsyncClient):
    """빈 이름으로 카테고리 생성 시 422 에러가 발생하는지 확인한다."""
    response = await client.post(
        "/api/categories",
        json={"name": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_category_too_long_name(client: AsyncClient):
    """51자 이상의 이름으로 카테고리 생성 시 422 에러가 발생하는지 확인한다."""
    long_name = "a" * 51
    response = await client.post(
        "/api/categories",
        json={"name": long_name},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 카테고리 조회 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_categories_empty(client: AsyncClient):
    """카테고리가 없을 때 빈 리스트를 반환하는지 확인한다."""
    response = await client.get("/api/categories")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient):
    """카테고리 목록 조회가 정상 동작하는지 확인한다."""
    await client.post("/api/categories", json={"name": "업무"})
    await client.post("/api/categories", json={"name": "개인"})
    await client.post("/api/categories", json={"name": "학습"})

    response = await client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # 이름순 정렬 확인
    names = [cat["name"] for cat in data]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# 카테고리 삭제 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_category(client: AsyncClient):
    """카테고리 삭제가 정상 동작하는지 확인한다."""
    r = await client.post("/api/categories", json={"name": "삭제할 카테고리"})
    category_id = r.json()["id"]

    response = await client.delete(f"/api/categories/{category_id}")
    assert response.status_code == 204

    # 삭제 후 목록에 없는지 확인
    list_response = await client.get("/api/categories")
    assert len(list_response.json()) == 0


@pytest.mark.asyncio
async def test_delete_category_not_found(client: AsyncClient):
    """존재하지 않는 카테고리 삭제 시 404 에러가 발생하는지 확인한다."""
    response = await client.delete("/api/categories/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_category_sets_todos_null(client: AsyncClient):
    """카테고리 삭제 시 연결된 TODO의 category_id가 NULL로 변경되는지 확인한다."""
    # 카테고리 생성
    cat_response = await client.post("/api/categories", json={"name": "업무"})
    category_id = cat_response.json()["id"]

    # 카테고리가 연결된 TODO 생성
    todo_response = await client.post(
        "/api/todos",
        json={"title": "업무 TODO", "category_id": category_id},
    )
    todo_id = todo_response.json()["id"]

    # 카테고리 삭제
    delete_response = await client.delete(f"/api/categories/{category_id}")
    assert delete_response.status_code == 204

    # TODO의 category_id가 NULL로 변경되었는지 확인
    todos_response = await client.get("/api/todos")
    todos = todos_response.json()
    assert len(todos) == 1
    assert todos[0]["id"] == todo_id
    assert todos[0]["category_id"] is None
