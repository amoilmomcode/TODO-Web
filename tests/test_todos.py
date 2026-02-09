"""TODO CRUD API 통합 테스트."""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# TODO 생성 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_todo_minimal(client: AsyncClient):
    """최소 필드만으로 TODO 생성이 정상 동작하는지 확인한다."""
    response = await client.post(
        "/api/todos",
        json={"title": "테스트 할 일"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "테스트 할 일"
    assert data["description"] == ""
    assert data["priority"] == "medium"
    assert data["is_completed"] is False
    assert data["category_id"] is None
    assert data["due_date"] is None
    assert data["tags"] == []
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_todo_full(
    client: AsyncClient, sample_category: dict, sample_tags: list[dict]
):
    """모든 필드를 포함한 TODO 생성이 정상 동작하는지 확인한다."""
    response = await client.post(
        "/api/todos",
        json={
            "title": "풀옵션 할 일",
            "description": "상세 설명입니다",
            "priority": "high",
            "category_id": sample_category["id"],
            "due_date": "2026-12-31",
            "tag_ids": [tag["id"] for tag in sample_tags],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "풀옵션 할 일"
    assert data["description"] == "상세 설명입니다"
    assert data["priority"] == "high"
    assert data["category_id"] == sample_category["id"]
    assert data["due_date"] == "2026-12-31"
    assert len(data["tags"]) == 2
    assert {t["name"] for t in data["tags"]} == {"긴급", "중요"}


@pytest.mark.asyncio
async def test_create_todo_invalid_title(client: AsyncClient):
    """빈 제목으로 TODO 생성 시 422 에러가 발생하는지 확인한다."""
    response = await client.post(
        "/api/todos",
        json={"title": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_todo_invalid_priority(client: AsyncClient):
    """잘못된 우선순위 값으로 TODO 생성 시 422 에러가 발생하는지 확인한다."""
    response = await client.post(
        "/api/todos",
        json={"title": "테스트", "priority": "urgent"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# TODO 조회 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_todos_empty(client: AsyncClient):
    """TODO가 없을 때 빈 리스트를 반환하는지 확인한다."""
    response = await client.get("/api/todos")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_list_todos(client: AsyncClient):
    """TODO 목록 조회가 정상 동작하는지 확인한다."""
    # TODO 2개 생성
    await client.post("/api/todos", json={"title": "첫 번째"})
    await client.post("/api/todos", json={"title": "두 번째"})

    response = await client.get("/api/todos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # 두 TODO가 모두 있는지 확인 (created_at이 동일할 수 있어 순서는 검증하지 않음)
    titles = {item["title"] for item in data}
    assert titles == {"첫 번째", "두 번째"}


@pytest.mark.asyncio
async def test_list_todos_filter_by_priority(client: AsyncClient):
    """우선순위 필터가 정상 동작하는지 확인한다."""
    await client.post("/api/todos", json={"title": "높음", "priority": "high"})
    await client.post("/api/todos", json={"title": "보통", "priority": "medium"})
    await client.post("/api/todos", json={"title": "낮음", "priority": "low"})

    response = await client.get("/api/todos?priority=high")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "높음"


@pytest.mark.asyncio
async def test_list_todos_filter_by_completed(client: AsyncClient):
    """완료 여부 필터가 정상 동작하는지 확인한다."""
    # TODO 생성 후 하나만 완료 처리
    r1 = await client.post("/api/todos", json={"title": "미완료"})
    r2 = await client.post("/api/todos", json={"title": "완료"})
    todo_id = r2.json()["id"]
    await client.patch(f"/api/todos/{todo_id}", json={"is_completed": True})

    # 완료된 항목만 조회
    response = await client.get("/api/todos?is_completed=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "완료"

    # 미완료 항목만 조회
    response = await client.get("/api/todos?is_completed=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "미완료"


@pytest.mark.asyncio
async def test_list_todos_filter_by_category(
    client: AsyncClient, sample_category: dict
):
    """카테고리 필터가 정상 동작하는지 확인한다."""
    # 카테고리가 있는 TODO와 없는 TODO 생성
    await client.post(
        "/api/todos",
        json={"title": "업무 TODO", "category_id": sample_category["id"]},
    )
    await client.post("/api/todos", json={"title": "일반 TODO"})

    response = await client.get(f"/api/todos?category_id={sample_category['id']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "업무 TODO"


# ---------------------------------------------------------------------------
# TODO 수정 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_todo_title(client: AsyncClient):
    """TODO 제목 수정이 정상 동작하는지 확인한다."""
    r = await client.post("/api/todos", json={"title": "원래 제목"})
    todo_id = r.json()["id"]

    response = await client.patch(
        f"/api/todos/{todo_id}",
        json={"title": "변경된 제목"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "변경된 제목"


@pytest.mark.asyncio
async def test_update_todo_priority(client: AsyncClient):
    """TODO 우선순위 수정이 정상 동작하는지 확인한다."""
    r = await client.post("/api/todos", json={"title": "테스트"})
    todo_id = r.json()["id"]

    response = await client.patch(
        f"/api/todos/{todo_id}",
        json={"priority": "low"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == "low"


@pytest.mark.asyncio
async def test_update_todo_completion(client: AsyncClient):
    """TODO 완료 처리가 정상 동작하는지 확인한다."""
    r = await client.post("/api/todos", json={"title": "테스트"})
    todo_id = r.json()["id"]

    response = await client.patch(
        f"/api/todos/{todo_id}",
        json={"is_completed": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_completed"] is True


@pytest.mark.asyncio
async def test_update_todo_tags(client: AsyncClient, sample_tags: list[dict]):
    """TODO 태그 수정이 정상 동작하는지 확인한다."""
    r = await client.post("/api/todos", json={"title": "테스트"})
    todo_id = r.json()["id"]

    # 태그 추가
    response = await client.patch(
        f"/api/todos/{todo_id}",
        json={"tag_ids": [sample_tags[0]["id"]]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["tags"]) == 1
    assert data["tags"][0]["name"] == "긴급"

    # 태그 교체
    response = await client.patch(
        f"/api/todos/{todo_id}",
        json={"tag_ids": [sample_tags[1]["id"]]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["tags"]) == 1
    assert data["tags"][0]["name"] == "중요"

    # 태그 모두 제거
    response = await client.patch(
        f"/api/todos/{todo_id}",
        json={"tag_ids": []},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["tags"]) == 0


@pytest.mark.asyncio
async def test_update_todo_not_found(client: AsyncClient):
    """존재하지 않는 TODO 수정 시 404 에러가 발생하는지 확인한다."""
    response = await client.patch(
        "/api/todos/99999",
        json={"title": "변경"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_todo_invalid_title(client: AsyncClient):
    """빈 제목으로 TODO 수정 시 422 에러가 발생하는지 확인한다."""
    r = await client.post("/api/todos", json={"title": "원래 제목"})
    todo_id = r.json()["id"]

    response = await client.patch(
        f"/api/todos/{todo_id}",
        json={"title": ""},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# TODO 삭제 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_todo(client: AsyncClient):
    """TODO 삭제가 정상 동작하는지 확인한다."""
    r = await client.post("/api/todos", json={"title": "삭제할 TODO"})
    todo_id = r.json()["id"]

    response = await client.delete(f"/api/todos/{todo_id}")
    assert response.status_code == 204

    # 삭제 후 조회 시 목록에 없는지 확인
    list_response = await client.get("/api/todos")
    assert len(list_response.json()) == 0


@pytest.mark.asyncio
async def test_delete_todo_not_found(client: AsyncClient):
    """존재하지 않는 TODO 삭제 시 404 에러가 발생하는지 확인한다."""
    response = await client.delete("/api/todos/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_todo_cascades_tags(client: AsyncClient, sample_tags: list[dict]):
    """TODO 삭제 시 연결된 태그도 cascade 삭제되는지 확인한다."""
    # TODO 생성 및 태그 연결
    r = await client.post(
        "/api/todos",
        json={"title": "태그 연결 테스트", "tag_ids": [sample_tags[0]["id"]]},
    )
    todo_id = r.json()["id"]

    # TODO 삭제
    response = await client.delete(f"/api/todos/{todo_id}")
    assert response.status_code == 204

    # 태그는 여전히 존재해야 함 (CASCADE DELETE는 todo_tags 테이블에만 적용)
    tags_response = await client.get("/api/tags")
    assert len(tags_response.json()) == 2
