"""엣지 케이스 및 추가 통합 테스트."""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# 유효성 검증 엣지 케이스
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_todo_with_no_fields(client: AsyncClient):
    """유효한 필드 없이 TODO 수정 시 아무 변경도 일어나지 않는지 확인한다.

    NOTE: 현재 구현은 tag_ids만 있어도 처리되므로 완전히 빈 객체로 테스트한다.
    """
    # TODO 생성
    response = await client.post(
        "/api/todos",
        json={"title": "원본 제목", "priority": "high"},
    )
    assert response.status_code == 201
    todo_id = response.json()["id"]
    original_title = response.json()["title"]

    # 빈 객체로 PATCH 요청 (아무것도 변경하지 않음)
    response = await client.patch(
        f"/api/todos/{todo_id}",
        json={},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == original_title
    assert data["priority"] == "high"


@pytest.mark.asyncio
async def test_create_todo_with_invalid_due_date(client: AsyncClient):
    """잘못된 날짜 형식으로 TODO 생성 시 422 에러가 발생하는지 확인한다."""
    response = await client.post(
        "/api/todos",
        json={"title": "날짜 테스트", "due_date": "invalid-date"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_todo_with_nonexistent_category(client: AsyncClient):
    """존재하지 않는 카테고리 ID로 TODO 생성 시 400 에러가 발생하는지 확인한다."""
    response = await client.post(
        "/api/todos",
        json={"title": "존재하지 않는 카테고리", "category_id": 99999},
    )
    assert response.status_code == 400
    assert "유효하지 않은 카테고리 ID" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_todo_with_past_due_date(client: AsyncClient):
    """과거 날짜로 마감일 설정이 가능한지 확인한다."""
    response = await client.post(
        "/api/todos",
        json={"title": "과거 마감일 테스트"},
    )
    todo_id = response.json()["id"]

    # 과거 날짜로 설정 (비즈니스 로직상 제한이 없다면 허용)
    update_response = await client.patch(
        f"/api/todos/{todo_id}",
        json={"due_date": "2020-01-01"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["due_date"] == "2020-01-01"


# ---------------------------------------------------------------------------
# 복합 필터링 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_todos_multiple_filters(
    client: AsyncClient, sample_category: dict
):
    """여러 필터를 동시에 적용한 TODO 목록 조회를 확인한다."""
    # 다양한 조건의 TODO 생성
    completed_todo = await client.post(
        "/api/todos",
        json={
            "title": "완료된 높음 우선순위 업무",
            "priority": "high",
            "category_id": sample_category["id"],
        },
    )
    await client.post(
        "/api/todos",
        json={
            "title": "미완료 높음 우선순위 업무",
            "priority": "high",
            "category_id": sample_category["id"],
        },
    )
    # 첫 번째 TODO 완료 처리
    completed_id = completed_todo.json()["id"]
    await client.patch(f"/api/todos/{completed_id}", json={"is_completed": True})

    await client.post(
        "/api/todos",
        json={
            "title": "미완료 보통 우선순위 업무",
            "priority": "medium",
            "category_id": sample_category["id"],
        },
    )

    # 필터: 카테고리 + 우선순위 + 미완료
    response = await client.get(
        f"/api/todos?category_id={sample_category['id']}&priority=high&is_completed=false"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "미완료 높음 우선순위 업무"
    assert data[0]["priority"] == "high"
    assert data[0]["is_completed"] is False


# ---------------------------------------------------------------------------
# 동시성 및 순서 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_multiple_todos_same_title(client: AsyncClient):
    """같은 제목으로 여러 TODO를 생성할 수 있는지 확인한다."""
    response1 = await client.post("/api/todos", json={"title": "중복 제목"})
    response2 = await client.post("/api/todos", json={"title": "중복 제목"})
    response3 = await client.post("/api/todos", json={"title": "중복 제목"})

    assert response1.status_code == 201
    assert response2.status_code == 201
    assert response3.status_code == 201

    # ID는 모두 달라야 함
    id1 = response1.json()["id"]
    id2 = response2.json()["id"]
    id3 = response3.json()["id"]
    assert len({id1, id2, id3}) == 3


@pytest.mark.asyncio
async def test_update_same_todo_multiple_times(client: AsyncClient):
    """같은 TODO를 여러 번 수정할 수 있는지 확인한다."""
    response = await client.post("/api/todos", json={"title": "초기 제목"})
    todo_id = response.json()["id"]

    # 여러 번 수정
    await client.patch(f"/api/todos/{todo_id}", json={"title": "수정1"})
    await client.patch(f"/api/todos/{todo_id}", json={"title": "수정2"})
    final_response = await client.patch(
        f"/api/todos/{todo_id}", json={"title": "최종 수정"}
    )

    assert final_response.status_code == 200
    assert final_response.json()["title"] == "최종 수정"


# ---------------------------------------------------------------------------
# 카테고리 특수 케이스
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_category_name_with_special_characters(client: AsyncClient):
    """특수 문자가 포함된 카테고리 이름 생성을 확인한다."""
    response = await client.post(
        "/api/categories",
        json={"name": "🔥 긴급 업무 (중요)"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "🔥 긴급 업무 (중요)"


@pytest.mark.asyncio
async def test_delete_category_with_multiple_todos(client: AsyncClient):
    """여러 TODO가 연결된 카테고리 삭제 시 모두 NULL로 변경되는지 확인한다."""
    # 카테고리 생성
    cat_response = await client.post("/api/categories", json={"name": "테스트 카테고리"})
    category_id = cat_response.json()["id"]

    # 여러 TODO 생성
    await client.post(
        "/api/todos", json={"title": "TODO 1", "category_id": category_id}
    )
    await client.post(
        "/api/todos", json={"title": "TODO 2", "category_id": category_id}
    )
    await client.post(
        "/api/todos", json={"title": "TODO 3", "category_id": category_id}
    )

    # 카테고리 삭제
    delete_response = await client.delete(f"/api/categories/{category_id}")
    assert delete_response.status_code == 204

    # 모든 TODO의 category_id가 NULL인지 확인
    todos_response = await client.get("/api/todos")
    todos = todos_response.json()
    assert len(todos) == 3
    assert all(todo["category_id"] is None for todo in todos)


# ---------------------------------------------------------------------------
# 태그 특수 케이스
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tag_name_with_special_characters(client: AsyncClient):
    """특수 문자가 포함된 태그 이름 생성을 확인한다."""
    response = await client.post(
        "/api/tags",
        json={"name": "#긴급 @중요"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "#긴급 @중요"


@pytest.mark.asyncio
async def test_update_todo_with_many_tags(client: AsyncClient):
    """TODO에 많은 태그를 연결할 수 있는지 확인한다."""
    # 여러 태그 생성
    tag_ids = []
    for i in range(10):
        tag_response = await client.post("/api/tags", json={"name": f"태그{i}"})
        tag_ids.append(tag_response.json()["id"])

    # TODO 생성 및 모든 태그 연결
    todo_response = await client.post(
        "/api/todos",
        json={"title": "많은 태그 테스트", "tag_ids": tag_ids},
    )

    assert todo_response.status_code == 201
    data = todo_response.json()
    assert len(data["tags"]) == 10


@pytest.mark.asyncio
async def test_clear_tags_then_add_again(client: AsyncClient, sample_todo: dict):
    """태그를 모두 제거한 후 다시 추가할 수 있는지 확인한다."""
    # 태그 생성
    tag1 = await client.post("/api/tags", json={"name": "태그A"})
    tag2 = await client.post("/api/tags", json={"name": "태그B"})
    tag1_id = tag1.json()["id"]
    tag2_id = tag2.json()["id"]

    # 태그 추가
    response = await client.patch(
        f"/api/todos/{sample_todo['id']}",
        json={"tag_ids": [tag1_id, tag2_id]},
    )
    assert len(response.json()["tags"]) == 2

    # 모든 태그 제거
    response = await client.patch(
        f"/api/todos/{sample_todo['id']}",
        json={"tag_ids": []},
    )
    assert len(response.json()["tags"]) == 0

    # 다시 태그 추가
    response = await client.patch(
        f"/api/todos/{sample_todo['id']}",
        json={"tag_ids": [tag1_id]},
    )
    assert len(response.json()["tags"]) == 1
    assert response.json()["tags"][0]["name"] == "태그A"


# ---------------------------------------------------------------------------
# SQL Injection 방어 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sql_injection_in_todo_title(client: AsyncClient):
    """SQL Injection 시도가 차단되는지 확인한다."""
    malicious_title = "'; DROP TABLE todos; --"

    response = await client.post(
        "/api/todos",
        json={"title": malicious_title},
    )
    assert response.status_code == 201

    # TODO가 정상적으로 생성되고 테이블은 유지되어야 함
    list_response = await client.get("/api/todos")
    assert list_response.status_code == 200
    todos = list_response.json()
    assert len(todos) == 1
    assert todos[0]["title"] == malicious_title


@pytest.mark.asyncio
async def test_sql_injection_in_category_name(client: AsyncClient):
    """카테고리 이름에 SQL Injection 시도가 차단되는지 확인한다."""
    malicious_name = "업무' OR '1'='1"

    response = await client.post(
        "/api/categories",
        json={"name": malicious_name},
    )
    assert response.status_code == 201

    # 카테고리 목록 조회 시 정상 동작해야 함
    list_response = await client.get("/api/categories")
    assert list_response.status_code == 200
    categories = list_response.json()
    assert len(categories) == 1
    assert categories[0]["name"] == malicious_name
