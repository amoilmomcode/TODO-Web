"""고아 TODO 레코드 방지 테스트.

잘못된 tag_ids로 TODO 생성/수정 시 고아 레코드가 남지 않는지 검증한다.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_post_invalid_tags_no_orphan_todo(client: AsyncClient):
    """존재하지 않는 tag_id로 TODO 생성 시 TODO가 DB에 남지 않아야 한다."""
    # 잘못된 태그로 TODO 생성 시도
    response = await client.post(
        "/api/todos",
        json={"title": "고아될 TODO", "tag_ids": [99999]},
    )
    assert response.status_code == 400

    # DB에 TODO가 남지 않았는지 확인
    list_response = await client.get("/api/todos")
    assert list_response.status_code == 200
    todos = list_response.json()
    assert len(todos) == 0, f"고아 TODO가 발견됨: {todos}"


@pytest.mark.asyncio
async def test_post_mixed_valid_invalid_tags_no_orphan(
    client: AsyncClient, sample_tags: list[dict]
):
    """유효 + 무효 태그 조합으로 TODO 생성 시 TODO가 남지 않아야 한다."""
    valid_id = sample_tags[0]["id"]
    invalid_id = 99999

    response = await client.post(
        "/api/todos",
        json={"title": "혼합 태그 TODO", "tag_ids": [valid_id, invalid_id]},
    )
    assert response.status_code == 400

    list_response = await client.get("/api/todos")
    todos = list_response.json()
    assert len(todos) == 0, f"고아 TODO가 발견됨: {todos}"


@pytest.mark.asyncio
async def test_post_valid_tags_still_works(
    client: AsyncClient, sample_tags: list[dict]
):
    """유효한 태그로 TODO 생성은 정상 동작해야 한다."""
    tag_ids = [t["id"] for t in sample_tags]

    response = await client.post(
        "/api/todos",
        json={"title": "정상 TODO", "tag_ids": tag_ids},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "정상 TODO"
    assert len(data["tags"]) == 2


@pytest.mark.asyncio
async def test_patch_invalid_tags_preserves_original(
    client: AsyncClient, sample_todo: dict, sample_tags: list[dict]
):
    """존재하지 않는 tag_id로 TODO 수정 시 기존 상태가 보존되어야 한다."""
    todo_id = sample_todo["id"]

    # 먼저 유효한 태그 설정
    valid_ids = [t["id"] for t in sample_tags]
    patch_ok = await client.patch(
        f"/api/todos/{todo_id}",
        json={"tag_ids": valid_ids},
    )
    assert patch_ok.status_code == 200

    # 잘못된 태그로 수정 시도
    patch_fail = await client.patch(
        f"/api/todos/{todo_id}",
        json={"tag_ids": [99999]},
    )
    assert patch_fail.status_code == 400

    # 기존 태그가 유지되는지 확인
    get_response = await client.get("/api/todos")
    todos = get_response.json()
    todo = next(t for t in todos if t["id"] == todo_id)
    assert len(todo["tags"]) == 2, "잘못된 수정 후 기존 태그가 사라짐"


@pytest.mark.asyncio
async def test_patch_invalid_tags_preserves_title_change(
    client: AsyncClient, sample_todo: dict
):
    """잘못된 태그 + 제목 변경 동시 요청 시 둘 다 반영되지 않아야 한다."""
    todo_id = sample_todo["id"]
    original_title = sample_todo["title"]

    response = await client.patch(
        f"/api/todos/{todo_id}",
        json={"title": "변경된 제목", "tag_ids": [99999]},
    )
    assert response.status_code == 400

    # 제목이 변경되지 않았는지 확인
    get_response = await client.get("/api/todos")
    todos = get_response.json()
    todo = next(t for t in todos if t["id"] == todo_id)
    # 참고: 현재 구현에서는 태그 검증이 UPDATE 전에 수행되므로 제목도 안 바뀜
    assert todo["title"] == original_title, "태그 실패 시 제목까지 변경되면 안 됨"
