"""QA 리뷰 테스트 — 도현 작성

코드 리뷰에서 발견한 버그, 보안 취약점, 엣지 케이스를 검증한다.

발견 사항:
1. 쿼리 파라미터 필터링 버그 (alias vs field_name)
2. 존재하지 않는 태그 ID로 TODO 생성 시 500 에러 (400이어야 함)
3. update_todo에서 존재하지 않는 ID에 대한 UPDATE 실행 후 None 반환 문제
4. set_todo_tags에서 존재하지 않는 tag_id 사용 시 IntegrityError 미처리
5. 카테고리/태그 삭제 후 TODO 목록 응답의 일관성
6. TODO 삭제 시 204 반환 후 실제 삭제 재확인
7. 프론트엔드 api.js의 createTodo에서 snake_case로 전송하는 문제
8. CORS 전체 허용 보안 이슈
9. 달력 뷰 TODO title XSS 미이스케이프 (calendar-todo-item)
"""

import pytest
import pytest_asyncio
from datetime import date, timedelta
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────
# BUG-001: 쿼리 파라미터 필터링 — alias vs snake_case
# ─────────────────────────────────────────────────────────────────


class TestQueryParameterFiltering:
    """쿼리 파라미터 alias와 snake_case 양쪽 모두 동작하는지 검증한다.

    FastAPI Query에 alias를 설정하면 alias 이름으로만 파라미터를 받는다.
    프론트엔드는 camelCase(alias)로 보내므로 정상이지만,
    REST API 직접 호출 시 snake_case로 보내면 필터가 무시된다.
    """

    async def test_filter_category_by_snake_case(
        self, client: AsyncClient
    ):
        """snake_case(category_id)로 카테고리 필터가 동작하는지 확인한다."""
        cat = await client.post("/api/categories", json={"name": "업무"})
        cat_id = cat.json()["id"]

        await client.post(
            "/api/todos",
            json={"title": "업무 할일", "category_id": cat_id},
        )
        await client.post("/api/todos", json={"title": "일반 할일"})

        # snake_case로 필터
        response = await client.get(f"/api/todos?category_id={cat_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "업무 할일"

    async def test_filter_is_completed_by_snake_case(self, client: AsyncClient):
        """snake_case(is_completed)로 완료 여부 필터가 동작하는지 확인한다."""
        await client.post("/api/todos", json={"title": "미완료"})
        r = await client.post("/api/todos", json={"title": "완료"})
        await client.patch(
            f"/api/todos/{r.json()['id']}", json={"is_completed": True}
        )

        response = await client.get("/api/todos?is_completed=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "완료"


# ─────────────────────────────────────────────────────────────────
# BUG-002: 존재하지 않는 태그 ID로 TODO 생성 시 500 에러
# ─────────────────────────────────────────────────────────────────


class TestNonexistentTagHandling:
    """존재하지 않는 태그 ID로 TODO 생성/수정 시 적절한 에러 응답을 검증한다."""

    async def test_create_todo_with_nonexistent_tag_ids(
        self, client: AsyncClient
    ):
        """BUG-002: 존재하지 않는 태그 ID로 TODO 생성 시 400 에러를 반환한다."""
        resp = await client.post(
            "/api/todos",
            json={"title": "태그 버그 테스트", "tagIds": [99999]},
        )
        assert resp.status_code == 400
        assert "유효하지 않은 태그 ID" in resp.json()["detail"]

    async def test_update_todo_with_nonexistent_tag_ids(
        self, client: AsyncClient
    ):
        """BUG-002: 존재하지 않는 태그 ID로 TODO 수정 시 400 에러를 반환한다."""
        r = await client.post("/api/todos", json={"title": "수정 대상"})
        todo_id = r.json()["id"]

        resp = await client.patch(
            f"/api/todos/{todo_id}",
            json={"tagIds": [99999]},
        )
        assert resp.status_code == 400
        assert "유효하지 않은 태그 ID" in resp.json()["detail"]


# ─────────────────────────────────────────────────────────────────
# BUG-003: update_todo 필드 없을 때 동작 이상
# ─────────────────────────────────────────────────────────────────


class TestUpdateTodoEdgeCases:
    """update_todo 함수의 엣지 케이스를 검증한다."""

    async def test_update_nonexistent_todo_tag_only(
        self, client: AsyncClient
    ):
        """존재하지 않는 TODO에 태그만 수정 요청 시 404를 반환하는지 확인한다."""
        tag = await client.post("/api/tags", json={"name": "테스트"})
        tag_id = tag.json()["id"]

        response = await client.patch(
            "/api/todos/99999",
            json={"tagIds": [tag_id]},
        )
        assert response.status_code == 404

    async def test_update_with_invalid_category_id(
        self, client: AsyncClient
    ):
        """존재하지 않는 카테고리 ID로 TODO 수정 시 400을 반환하는지 확인한다."""
        r = await client.post("/api/todos", json={"title": "테스트"})
        todo_id = r.json()["id"]

        response = await client.patch(
            f"/api/todos/{todo_id}",
            json={"categoryId": 99999},
        )
        assert response.status_code == 400
        assert "유효하지 않은 카테고리 ID" in response.json()["detail"]

    async def test_update_multiple_fields_at_once(
        self, client: AsyncClient
    ):
        """여러 필드를 동시에 수정할 수 있는지 확인한다."""
        cat = await client.post("/api/categories", json={"name": "업무"})
        tag = await client.post("/api/tags", json={"name": "긴급"})
        r = await client.post("/api/todos", json={"title": "원본"})
        todo_id = r.json()["id"]

        response = await client.patch(
            f"/api/todos/{todo_id}",
            json={
                "title": "변경된 제목",
                "description": "새 설명",
                "priority": "high",
                "isCompleted": True,
                "categoryId": cat.json()["id"],
                "dueDate": "2026-12-31",
                "tagIds": [tag.json()["id"]],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "변경된 제목"
        assert data["description"] == "새 설명"
        assert data["priority"] == "high"
        assert data["is_completed"] is True
        assert data["category_id"] == cat.json()["id"]
        assert data["due_date"] == "2026-12-31"
        assert len(data["tags"]) == 1


# ─────────────────────────────────────────────────────────────────
# BUG-004: 프론트엔드 api.js createTodo snake_case 전송 문제
# ─────────────────────────────────────────────────────────────────


class TestApiKeyNaming:
    """API에서 camelCase와 snake_case 요청 본문 모두 처리하는지 검증한다.

    프론트엔드 api.js의 createTodo 함수가 snake_case(category_id, due_date, tag_ids)로
    전송하고 있으며, Pydantic 모델에 populate_by_name=True 설정 덕분에
    snake_case도 인식된다. 이 동작을 검증한다.
    """

    async def test_create_todo_with_snake_case_body(
        self, client: AsyncClient
    ):
        """snake_case 키로 TODO 생성이 가능한지 확인한다."""
        cat = await client.post("/api/categories", json={"name": "테스트"})
        tag = await client.post("/api/tags", json={"name": "태그"})

        response = await client.post(
            "/api/todos",
            json={
                "title": "snake_case 테스트",
                "description": "설명",
                "priority": "high",
                "category_id": cat.json()["id"],
                "due_date": "2026-06-15",
                "tag_ids": [tag.json()["id"]],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["category_id"] == cat.json()["id"]
        assert data["due_date"] == "2026-06-15"
        assert len(data["tags"]) == 1

    async def test_create_todo_with_camelCase_body(
        self, client: AsyncClient
    ):
        """camelCase 키로 TODO 생성이 가능한지 확인한다."""
        cat = await client.post("/api/categories", json={"name": "테스트"})
        tag = await client.post("/api/tags", json={"name": "태그"})

        response = await client.post(
            "/api/todos",
            json={
                "title": "camelCase 테스트",
                "description": "설명",
                "priority": "high",
                "categoryId": cat.json()["id"],
                "dueDate": "2026-06-15",
                "tagIds": [tag.json()["id"]],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["category_id"] == cat.json()["id"]
        assert data["due_date"] == "2026-06-15"
        assert len(data["tags"]) == 1

    async def test_update_todo_with_snake_case_body(
        self, client: AsyncClient
    ):
        """snake_case 키로 TODO 수정이 가능한지 확인한다."""
        r = await client.post("/api/todos", json={"title": "원본"})
        todo_id = r.json()["id"]

        response = await client.patch(
            f"/api/todos/{todo_id}",
            json={"is_completed": True, "due_date": "2026-12-31"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_completed"] is True
        assert data["due_date"] == "2026-12-31"

    async def test_update_todo_with_camelCase_body(
        self, client: AsyncClient
    ):
        """camelCase 키로 TODO 수정이 가능한지 확인한다."""
        r = await client.post("/api/todos", json={"title": "원본"})
        todo_id = r.json()["id"]

        response = await client.patch(
            f"/api/todos/{todo_id}",
            json={"isCompleted": True, "dueDate": "2026-12-31"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_completed"] is True
        assert data["due_date"] == "2026-12-31"


# ─────────────────────────────────────────────────────────────────
# BUG-005: 카테고리/태그 삭제 후 TODO 응답 일관성
# ─────────────────────────────────────────────────────────────────


class TestCascadeConsistency:
    """삭제 캐스케이드 후 데이터 일관성을 검증한다."""

    async def test_delete_tag_removes_from_todo_response(
        self, client: AsyncClient
    ):
        """태그 삭제 후 TODO 응답에서 해당 태그가 사라지는지 확인한다."""
        tag1 = await client.post("/api/tags", json={"name": "태그1"})
        tag2 = await client.post("/api/tags", json={"name": "태그2"})
        tag1_id = tag1.json()["id"]
        tag2_id = tag2.json()["id"]

        r = await client.post(
            "/api/todos",
            json={"title": "태그 삭제 테스트", "tagIds": [tag1_id, tag2_id]},
        )
        assert len(r.json()["tags"]) == 2

        # 태그1 삭제
        await client.delete(f"/api/tags/{tag1_id}")

        # TODO 조회 시 태그1이 빠져있어야 함
        response = await client.get("/api/todos")
        todos = response.json()
        todo = next(t for t in todos if t["id"] == r.json()["id"])
        assert len(todo["tags"]) == 1
        assert todo["tags"][0]["name"] == "태그2"

    async def test_delete_all_tags_leaves_todo_with_empty_tags(
        self, client: AsyncClient
    ):
        """모든 태그를 삭제하면 TODO 응답에 빈 태그 리스트가 반환되는지 확인한다."""
        tag = await client.post("/api/tags", json={"name": "삭제될태그"})
        tag_id = tag.json()["id"]

        r = await client.post(
            "/api/todos",
            json={"title": "태그 전체 삭제", "tagIds": [tag_id]},
        )

        # 태그 삭제
        await client.delete(f"/api/tags/{tag_id}")

        # TODO 조회
        response = await client.get("/api/todos")
        todo = response.json()[0]
        assert todo["tags"] == []

    async def test_delete_category_nullifies_multiple_todos(
        self, client: AsyncClient
    ):
        """카테고리 삭제 시 여러 TODO의 category_id가 NULL이 되는지 확인한다."""
        cat = await client.post("/api/categories", json={"name": "삭제될카테고리"})
        cat_id = cat.json()["id"]

        for i in range(5):
            await client.post(
                "/api/todos",
                json={"title": f"할일 {i}", "categoryId": cat_id},
            )

        await client.delete(f"/api/categories/{cat_id}")

        response = await client.get("/api/todos")
        for todo in response.json():
            assert todo["category_id"] is None


# ─────────────────────────────────────────────────────────────────
# 추가 보안 테스트
# ─────────────────────────────────────────────────────────────────


class TestSecurityAdditional:
    """추가 보안 검증 테스트."""

    async def test_xss_in_description(self, client: AsyncClient):
        """설명 필드에 XSS 페이로드가 그대로 저장되는지 확인한다.
        (프론트엔드에서 이스케이프 처리 필요)
        """
        xss = '<img src=x onerror="alert(1)">'
        r = await client.post(
            "/api/todos",
            json={"title": "XSS 테스트", "description": xss},
        )
        assert r.status_code == 201
        assert r.json()["description"] == xss

    async def test_xss_in_category_name(self, client: AsyncClient):
        """카테고리 이름에 XSS 페이로드가 그대로 저장되는지 확인한다."""
        xss = "<script>document.cookie</script>"
        r = await client.post("/api/categories", json={"name": xss})
        assert r.status_code == 201
        assert r.json()["name"] == xss

    async def test_xss_in_tag_name(self, client: AsyncClient):
        """태그 이름에 XSS 페이로드가 그대로 저장되는지 확인한다."""
        xss = '"><svg onload=alert(1)>'
        r = await client.post("/api/tags", json={"name": xss})
        assert r.status_code == 201
        assert r.json()["name"] == xss

    async def test_very_long_description(self, client: AsyncClient):
        """description 필드의 max_length=5000 제한이 동작하는지 확인한다."""
        # 5000자 이하는 정상 저장
        ok_desc = "A" * 5000
        r = await client.post(
            "/api/todos",
            json={"title": "정상 설명", "description": ok_desc},
        )
        assert r.status_code == 201
        assert len(r.json()["description"]) == 5000

        # 5001자 이상은 422 거부
        long_desc = "A" * 5001
        r = await client.post(
            "/api/todos",
            json={"title": "긴 설명", "description": long_desc},
        )
        assert r.status_code == 422

    async def test_negative_todo_id(self, client: AsyncClient):
        """음수 ID로 접근 시 적절한 응답을 반환하는지 확인한다."""
        response = await client.get("/api/todos")
        assert response.status_code == 200

        response = await client.patch(
            "/api/todos/-1", json={"title": "음수ID"}
        )
        assert response.status_code in (404, 422)

        response = await client.delete("/api/todos/-1")
        assert response.status_code in (404, 422)

    async def test_zero_todo_id(self, client: AsyncClient):
        """ID가 0인 경우 적절한 응답을 반환하는지 확인한다."""
        response = await client.patch(
            "/api/todos/0", json={"title": "제로ID"}
        )
        assert response.status_code in (404, 422)

    async def test_string_todo_id(self, client: AsyncClient):
        """문자열 ID로 접근 시 422 에러를 반환하는지 확인한다."""
        response = await client.patch(
            "/api/todos/abc", json={"title": "문자ID"}
        )
        assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────
# 응답 모델 검증
# ─────────────────────────────────────────────────────────────────


class TestResponseModel:
    """API 응답 모델이 일관되게 유지되는지 검증한다."""

    async def test_todo_response_has_all_fields(self, client: AsyncClient):
        """TODO 응답에 모든 필수 필드가 포함되는지 확인한다."""
        r = await client.post(
            "/api/todos",
            json={"title": "응답 모델 테스트"},
        )
        data = r.json()
        required_fields = {
            "id", "title", "description", "priority",
            "is_completed", "category_id", "due_date",
            "tags", "created_at", "updated_at",
        }
        assert required_fields.issubset(data.keys()), (
            f"누락된 필드: {required_fields - data.keys()}"
        )

    async def test_category_response_has_all_fields(
        self, client: AsyncClient
    ):
        """카테고리 응답에 모든 필수 필드가 포함되는지 확인한다."""
        r = await client.post("/api/categories", json={"name": "테스트"})
        data = r.json()
        required_fields = {"id", "name", "created_at"}
        assert required_fields.issubset(data.keys())

    async def test_tag_response_has_all_fields(self, client: AsyncClient):
        """태그 응답에 모든 필수 필드가 포함되는지 확인한다."""
        r = await client.post("/api/tags", json={"name": "테스트"})
        data = r.json()
        required_fields = {"id", "name"}
        assert required_fields.issubset(data.keys())

    async def test_todo_list_order_is_newest_first(
        self, client: AsyncClient
    ):
        """BUG-003: TODO 목록이 최신 순(created_at DESC)으로 정렬되는지 확인한다.

        NOTE: SQLite의 CURRENT_TIMESTAMP는 초 단위 해상도이므로,
        같은 초에 생성된 TODO들은 created_at이 동일하다.
        이 경우 ORDER BY created_at DESC는 ID 오름차순으로 반환될 수 있다.
        실제 운영 환경에서는 문제가 되지 않지만, 테스트에서는 재현된다.
        """
        await client.post("/api/todos", json={"title": "첫번째"})
        await client.post("/api/todos", json={"title": "두번째"})
        await client.post("/api/todos", json={"title": "세번째"})

        response = await client.get("/api/todos")
        data = response.json()
        ids = [t["id"] for t in data]
        # 같은 초에 생성되어도 id DESC로 최신 항목이 먼저 나와야 함
        assert ids == sorted(ids, reverse=True), (
            "같은 초에 생성된 TODO가 최신순(id DESC)으로 정렬되지 않았습니다."
        )


# ─────────────────────────────────────────────────────────────────
# 달력 뷰 관련 데이터 검증
# ─────────────────────────────────────────────────────────────────


class TestCalendarDataIntegrity:
    """달력 뷰에 필요한 데이터 무결성을 검증한다."""

    async def test_due_date_format_consistency(self, client: AsyncClient):
        """마감일 형식이 일관되게 YYYY-MM-DD로 반환되는지 확인한다."""
        r = await client.post(
            "/api/todos",
            json={"title": "날짜 포맷", "dueDate": "2026-03-15"},
        )
        assert r.json()["due_date"] == "2026-03-15"

    async def test_multiple_todos_same_due_date(self, client: AsyncClient):
        """같은 마감일에 여러 TODO가 있을 때 모두 정상 반환되는지 확인한다."""
        target_date = "2026-06-15"
        for i in range(5):
            await client.post(
                "/api/todos",
                json={"title": f"같은날 {i}", "dueDate": target_date},
            )

        response = await client.get("/api/todos")
        todos_on_date = [
            t for t in response.json()
            if t["due_date"] == target_date
        ]
        assert len(todos_on_date) == 5

    async def test_completed_todo_still_has_due_date(
        self, client: AsyncClient
    ):
        """완료 처리된 TODO의 마감일이 유지되는지 확인한다."""
        r = await client.post(
            "/api/todos",
            json={"title": "완료 마감일", "dueDate": "2026-07-20"},
        )
        todo_id = r.json()["id"]

        await client.patch(
            f"/api/todos/{todo_id}",
            json={"isCompleted": True},
        )

        response = await client.get("/api/todos")
        todo = next(t for t in response.json() if t["id"] == todo_id)
        assert todo["is_completed"] is True
        assert todo["due_date"] == "2026-07-20"

    async def test_update_due_date_to_null(self, client: AsyncClient):
        """마감일을 null로 변경할 수 있는지 확인한다."""
        r = await client.post(
            "/api/todos",
            json={"title": "마감일 제거", "dueDate": "2026-08-01"},
        )
        todo_id = r.json()["id"]
        assert r.json()["due_date"] == "2026-08-01"

        response = await client.patch(
            f"/api/todos/{todo_id}",
            json={"dueDate": None},
        )
        assert response.status_code == 200
        assert response.json()["due_date"] is None


# ─────────────────────────────────────────────────────────────────
# 동시 조작 시나리오
# ─────────────────────────────────────────────────────────────────


class TestConcurrentScenarios:
    """동시 또는 연속적인 조작 시나리오를 검증한다."""

    async def test_create_update_delete_cycle(self, client: AsyncClient):
        """생성 → 수정 → 삭제 전체 사이클이 정상 동작하는지 확인한다."""
        # 생성
        r = await client.post(
            "/api/todos",
            json={
                "title": "사이클 테스트",
                "priority": "low",
            },
        )
        assert r.status_code == 201
        todo_id = r.json()["id"]

        # 수정
        r = await client.patch(
            f"/api/todos/{todo_id}",
            json={"title": "수정됨", "priority": "high", "isCompleted": True},
        )
        assert r.status_code == 200
        assert r.json()["title"] == "수정됨"
        assert r.json()["is_completed"] is True

        # 삭제
        r = await client.delete(f"/api/todos/{todo_id}")
        assert r.status_code == 204

        # 삭제 후 조회 시 없어야 함
        r = await client.get("/api/todos")
        assert all(t["id"] != todo_id for t in r.json())

    async def test_delete_then_create_reuses_no_id(
        self, client: AsyncClient
    ):
        """삭제 후 재생성 시 새로운 ID가 부여되는지 확인한다."""
        r1 = await client.post("/api/todos", json={"title": "삭제될 항목"})
        old_id = r1.json()["id"]

        await client.delete(f"/api/todos/{old_id}")

        r2 = await client.post("/api/todos", json={"title": "새 항목"})
        new_id = r2.json()["id"]
        assert new_id != old_id

    async def test_rapid_toggle_completion(self, client: AsyncClient):
        """완료 상태를 빠르게 토글해도 정상 동작하는지 확인한다."""
        r = await client.post("/api/todos", json={"title": "토글 테스트"})
        todo_id = r.json()["id"]

        for expected in [True, False, True, False, True]:
            r = await client.patch(
                f"/api/todos/{todo_id}",
                json={"isCompleted": expected},
            )
            assert r.status_code == 200
            assert r.json()["is_completed"] is expected
