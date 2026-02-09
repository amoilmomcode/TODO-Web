"""태그 CRUD 및 TODO-태그 연결 API 통합 테스트."""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# 태그 생성 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_tag(client: AsyncClient):
    """태그 생성이 정상 동작하는지 확인한다."""
    response = await client.post(
        "/api/tags",
        json={"name": "긴급"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "긴급"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_tag_duplicate(client: AsyncClient):
    """중복된 태그 이름으로 생성 시 409 에러가 발생하는지 확인한다."""
    await client.post("/api/tags", json={"name": "긴급"})

    response = await client.post("/api/tags", json={"name": "긴급"})
    assert response.status_code == 409
    assert "이미 존재하는 태그입니다" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_tag_empty_name(client: AsyncClient):
    """빈 이름으로 태그 생성 시 422 에러가 발생하는지 확인한다."""
    response = await client.post(
        "/api/tags",
        json={"name": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_tag_too_long_name(client: AsyncClient):
    """31자 이상의 이름으로 태그 생성 시 422 에러가 발생하는지 확인한다."""
    long_name = "a" * 31
    response = await client.post(
        "/api/tags",
        json={"name": long_name},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 태그 조회 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tags_empty(client: AsyncClient):
    """태그가 없을 때 빈 리스트를 반환하는지 확인한다."""
    response = await client.get("/api/tags")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_tags(client: AsyncClient):
    """태그 목록 조회가 정상 동작하는지 확인한다."""
    await client.post("/api/tags", json={"name": "긴급"})
    await client.post("/api/tags", json={"name": "중요"})
    await client.post("/api/tags", json={"name": "일반"})

    response = await client.get("/api/tags")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # 이름순 정렬 확인
    names = [tag["name"] for tag in data]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# TODO-태그 연결 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_todo_with_tags_on_create(client: AsyncClient):
    """TODO 생성 시 태그 연결이 정상 동작하는지 확인한다."""
    # 태그 생성
    tag1 = await client.post("/api/tags", json={"name": "긴급"})
    tag2 = await client.post("/api/tags", json={"name": "중요"})
    tag1_id = tag1.json()["id"]
    tag2_id = tag2.json()["id"]

    # TODO 생성 시 태그 연결
    response = await client.post(
        "/api/todos",
        json={"title": "태그 연결 TODO", "tag_ids": [tag1_id, tag2_id]},
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["tags"]) == 2
    tag_names = {tag["name"] for tag in data["tags"]}
    assert tag_names == {"긴급", "중요"}


@pytest.mark.asyncio
async def test_todo_update_tags(client: AsyncClient, sample_todo: dict):
    """TODO 수정 시 태그 변경이 정상 동작하는지 확인한다."""
    # 태그 생성
    tag1 = await client.post("/api/tags", json={"name": "태그1"})
    tag2 = await client.post("/api/tags", json={"name": "태그2"})
    tag3 = await client.post("/api/tags", json={"name": "태그3"})
    tag1_id = tag1.json()["id"]
    tag2_id = tag2.json()["id"]
    tag3_id = tag3.json()["id"]

    # 태그 추가
    response = await client.patch(
        f"/api/todos/{sample_todo['id']}",
        json={"tag_ids": [tag1_id, tag2_id]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["tags"]) == 2

    # 태그 교체 (기존 태그는 제거되고 새 태그만 남음)
    response = await client.patch(
        f"/api/todos/{sample_todo['id']}",
        json={"tag_ids": [tag3_id]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["tags"]) == 1
    assert data["tags"][0]["name"] == "태그3"

    # 태그 모두 제거
    response = await client.patch(
        f"/api/todos/{sample_todo['id']}",
        json={"tag_ids": []},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["tags"]) == 0


@pytest.mark.asyncio
async def test_todo_tags_only_update(client: AsyncClient, sample_todo: dict):
    """TODO의 다른 필드는 변경하지 않고 태그만 수정할 수 있는지 확인한다."""
    original_title = sample_todo["title"]

    # 태그 생성
    tag = await client.post("/api/tags", json={"name": "태그"})
    tag_id = tag.json()["id"]

    # 태그만 변경
    response = await client.patch(
        f"/api/todos/{sample_todo['id']}",
        json={"tag_ids": [tag_id]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == original_title  # 제목은 그대로
    assert len(data["tags"]) == 1
    assert data["tags"][0]["name"] == "태그"


@pytest.mark.asyncio
async def test_delete_todo_removes_tag_associations(client: AsyncClient):
    """TODO 삭제 시 todo_tags 테이블의 연결도 CASCADE 삭제되는지 확인한다."""
    # 태그 생성
    tag = await client.post("/api/tags", json={"name": "테스트 태그"})
    tag_id = tag.json()["id"]

    # TODO 생성 및 태그 연결
    todo = await client.post(
        "/api/todos",
        json={"title": "삭제할 TODO", "tag_ids": [tag_id]},
    )
    todo_id = todo.json()["id"]

    # TODO 삭제
    await client.delete(f"/api/todos/{todo_id}")

    # 태그는 여전히 존재해야 함
    tags_response = await client.get("/api/tags")
    assert len(tags_response.json()) == 1

    # 새로운 TODO에 같은 태그를 다시 연결할 수 있어야 함
    new_todo = await client.post(
        "/api/todos",
        json={"title": "새 TODO", "tag_ids": [tag_id]},
    )
    assert new_todo.status_code == 201
    assert len(new_todo.json()["tags"]) == 1


@pytest.mark.asyncio
async def test_todo_with_nonexistent_tags(client: AsyncClient):
    """존재하지 않는 태그 ID로 TODO 생성 시 400 에러가 발생하는지 확인한다."""
    resp = await client.post(
        "/api/todos",
        json={"title": "태그 테스트", "tagIds": [99999]},
    )
    assert resp.status_code == 400
    assert "유효하지 않은 태그 ID" in resp.json()["detail"]
