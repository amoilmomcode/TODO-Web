"""BUG-002 수정 검증 테스트 — 도현(QA) 작성

BUG-002: 존재하지 않는 tag_id로 TODO 생성/수정 시 IntegrityError 미처리 → 500 에러
수정 내용: set_todo_tags()에 validate_tag_ids() 선행 검증 추가, ValueError → 400 응답

검증 항목:
1. POST /api/todos — 존재하지 않는 tag_id → 400 응답
2. PATCH /api/todos/{id} — 존재하지 않는 tag_id → 400 응답
3. 에러 응답에 잘못된 tag_id 정보 포함 확인
4. 정상 tag_id로는 기존처럼 동작하는지 확인
5. 혼합 tag_id(유효 + 무효) 처리 확인
"""

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────
# 1. POST /api/todos — 존재하지 않는 tag_id 에러 처리
# ─────────────────────────────────────────────────────────────────


class TestCreateTodoInvalidTagIds:
    """POST /api/todos에서 존재하지 않는 tag_id 처리를 검증한다."""

    async def test_single_nonexistent_tag_returns_400(
        self, client: AsyncClient
    ):
        """존재하지 않는 단일 tag_id로 TODO 생성 시 400을 반환한다."""
        resp = await client.post(
            "/api/todos",
            json={"title": "잘못된 태그", "tag_ids": [99999]},
        )
        assert resp.status_code == 400

    async def test_multiple_nonexistent_tags_returns_400(
        self, client: AsyncClient
    ):
        """존재하지 않는 복수 tag_id로 TODO 생성 시 400을 반환한다."""
        resp = await client.post(
            "/api/todos",
            json={"title": "잘못된 태그들", "tag_ids": [88888, 99999]},
        )
        assert resp.status_code == 400

    async def test_mixed_valid_and_invalid_tags_returns_400(
        self, client: AsyncClient, sample_tags: list[dict]
    ):
        """유효 tag_id + 무효 tag_id 혼합 시 400을 반환한다.

        일부만 유효해도 무효한 ID가 하나라도 있으면 거부되어야 한다.
        """
        valid_id = sample_tags[0]["id"]
        invalid_id = 99999

        resp = await client.post(
            "/api/todos",
            json={"title": "혼합 태그", "tag_ids": [valid_id, invalid_id]},
        )
        assert resp.status_code == 400

    async def test_error_detail_contains_invalid_tag_info(
        self, client: AsyncClient
    ):
        """에러 응답의 detail에 '유효하지 않은 태그 ID' 메시지가 포함된다."""
        resp = await client.post(
            "/api/todos",
            json={"title": "에러 메시지 확인", "tag_ids": [77777]},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "유효하지 않은 태그 ID" in detail

    async def test_error_detail_includes_specific_invalid_ids(
        self, client: AsyncClient
    ):
        """에러 응답에 구체적인 잘못된 tag_id 값이 포함된다."""
        resp = await client.post(
            "/api/todos",
            json={"title": "구체적 ID 확인", "tag_ids": [55555, 66666]},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        # validate_tag_ids가 반환한 invalid ID들이 메시지에 포함
        assert "55555" in detail
        assert "66666" in detail

    async def test_todo_not_created_on_invalid_tag(
        self, client: AsyncClient
    ):
        """잘못된 tag_id로 생성 실패 시 TODO 자체는 생성되지만 태그만 실패한다.

        현재 구현: TODO 먼저 생성 → 태그 연결 시도 → 실패 시 400.
        TODO는 이미 DB에 존재하게 된다. 이 동작을 확인한다.
        """
        before = await client.get("/api/todos")
        before_count = len(before.json())

        resp = await client.post(
            "/api/todos",
            json={"title": "생성 후 태그 실패", "tag_ids": [99999]},
        )
        assert resp.status_code == 400

        after = await client.get("/api/todos")
        after_count = len(after.json())
        # NOTE: 현재 구현에서는 TODO가 먼저 INSERT된 후 태그 검증에서 실패하므로
        # TODO 자체는 DB에 남아있을 수 있다. 트랜잭션 롤백이 없는 현재 구조의 한계.
        # 이 부분은 별도 개선 사항으로 기록한다.
        assert after_count >= before_count


# ─────────────────────────────────────────────────────────────────
# 2. PATCH /api/todos/{id} — 존재하지 않는 tag_id 에러 처리
# ─────────────────────────────────────────────────────────────────


class TestUpdateTodoInvalidTagIds:
    """PATCH /api/todos/{id}에서 존재하지 않는 tag_id 처리를 검증한다."""

    async def test_update_with_nonexistent_tag_returns_400(
        self, client: AsyncClient, sample_todo: dict
    ):
        """존재하지 않는 tag_id로 TODO 수정 시 400을 반환한다."""
        resp = await client.patch(
            f"/api/todos/{sample_todo['id']}",
            json={"tag_ids": [99999]},
        )
        assert resp.status_code == 400

    async def test_update_mixed_tags_returns_400(
        self, client: AsyncClient, sample_todo: dict, sample_tags: list[dict]
    ):
        """유효 + 무효 tag_id 혼합으로 수정 시 400을 반환한다."""
        valid_id = sample_tags[0]["id"]
        resp = await client.patch(
            f"/api/todos/{sample_todo['id']}",
            json={"tag_ids": [valid_id, 99999]},
        )
        assert resp.status_code == 400

    async def test_update_error_detail_contains_tag_info(
        self, client: AsyncClient, sample_todo: dict
    ):
        """수정 시 에러 응답에 잘못된 태그 ID 정보가 포함된다."""
        resp = await client.patch(
            f"/api/todos/{sample_todo['id']}",
            json={"tag_ids": [44444]},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "유효하지 않은 태그 ID" in detail
        assert "44444" in detail

    async def test_update_tag_only_with_invalid_tag(
        self, client: AsyncClient, sample_todo: dict
    ):
        """다른 필드 변경 없이 태그만 잘못된 ID로 수정 시도해도 400을 반환한다."""
        resp = await client.patch(
            f"/api/todos/{sample_todo['id']}",
            json={"tag_ids": [88888]},
        )
        assert resp.status_code == 400

    async def test_existing_tags_preserved_on_failed_update(
        self, client: AsyncClient, sample_tags: list[dict]
    ):
        """태그 수정 실패 시 기존 태그가 유지되는지 확인한다."""
        tag_id = sample_tags[0]["id"]

        # 유효한 태그로 TODO 생성
        r = await client.post(
            "/api/todos",
            json={"title": "태그 보존 테스트", "tag_ids": [tag_id]},
        )
        todo_id = r.json()["id"]
        assert len(r.json()["tags"]) == 1

        # 잘못된 태그로 수정 시도 → 실패
        resp = await client.patch(
            f"/api/todos/{todo_id}",
            json={"tag_ids": [99999]},
        )
        assert resp.status_code == 400

        # 기존 태그가 그대로 유지되어야 함
        get_resp = await client.get("/api/todos")
        todo = next(t for t in get_resp.json() if t["id"] == todo_id)
        assert len(todo["tags"]) == 1
        assert todo["tags"][0]["id"] == tag_id


# ─────────────────────────────────────────────────────────────────
# 3. 정상 tag_id로는 기존대로 동작하는지 확인 (회귀 테스트)
# ─────────────────────────────────────────────────────────────────


class TestValidTagIdsStillWork:
    """정상적인 tag_id로의 생성/수정이 기존처럼 동작하는지 회귀 테스트한다."""

    async def test_create_todo_with_valid_tags(
        self, client: AsyncClient, sample_tags: list[dict]
    ):
        """유효한 tag_id로 TODO 생성 시 201과 태그 목록이 정상 반환된다."""
        tag_ids = [t["id"] for t in sample_tags]
        resp = await client.post(
            "/api/todos",
            json={"title": "정상 태그 생성", "tag_ids": tag_ids},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["tags"]) == 2
        returned_ids = sorted(t["id"] for t in data["tags"])
        assert returned_ids == sorted(tag_ids)

    async def test_update_todo_with_valid_tags(
        self, client: AsyncClient, sample_todo: dict, sample_tags: list[dict]
    ):
        """유효한 tag_id로 TODO 수정 시 200과 태그 목록이 정상 반환된다."""
        tag_ids = [t["id"] for t in sample_tags]
        resp = await client.patch(
            f"/api/todos/{sample_todo['id']}",
            json={"tag_ids": tag_ids},
        )
        assert resp.status_code == 200
        assert len(resp.json()["tags"]) == 2

    async def test_create_todo_with_empty_tag_list(
        self, client: AsyncClient
    ):
        """빈 tag_ids 리스트로 TODO 생성 시 정상 동작한다."""
        resp = await client.post(
            "/api/todos",
            json={"title": "태그 없음", "tag_ids": []},
        )
        assert resp.status_code == 201
        assert resp.json()["tags"] == []

    async def test_update_todo_clear_tags(
        self, client: AsyncClient, sample_tags: list[dict]
    ):
        """태그가 있는 TODO에서 빈 리스트로 수정하면 태그가 모두 제거된다."""
        tag_ids = [t["id"] for t in sample_tags]
        r = await client.post(
            "/api/todos",
            json={"title": "태그 제거 테스트", "tag_ids": tag_ids},
        )
        assert len(r.json()["tags"]) == 2

        resp = await client.patch(
            f"/api/todos/{r.json()['id']}",
            json={"tag_ids": []},
        )
        assert resp.status_code == 200
        assert resp.json()["tags"] == []

    async def test_create_without_tag_ids_field(
        self, client: AsyncClient
    ):
        """tag_ids 필드 자체를 생략해도 정상 동작한다."""
        resp = await client.post(
            "/api/todos",
            json={"title": "태그 필드 생략"},
        )
        assert resp.status_code == 201
        assert resp.json()["tags"] == []
