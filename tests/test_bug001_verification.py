"""BUG-001 수정 검증 테스트 — snake_case 쿼리 파라미터 필터링

BUG-001 요약:
    GET /api/todos 엔드포인트에서 Query alias 설정 때문에
    snake_case 파라미터(category_id, is_completed)가 무시되는 버그.
    수정: list_todos가 Query()를 직접 사용하도록 변경하여 snake_case 정상 동작.

검증 항목:
    1. category_id 쿼리 파라미터로 필터링 동작 확인
    2. is_completed 쿼리 파라미터로 필터링 동작 확인
    3. priority 쿼리 파라미터 필터링 확인
    4. 복합 필터 조합 (category_id + is_completed + priority)
    5. 필터 미지정 시 전체 반환 확인
    6. 존재하지 않는 값으로 필터 시 빈 결과 반환 확인

작성: 도현 (QA)
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────
# 테스트 데이터 셋업 fixture
# ─────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def filter_dataset(client: AsyncClient) -> dict:
    """필터 테스트용 데이터셋을 생성한다.

    - 카테고리 2개 (업무, 개인)
    - TODO 4개:
        - "업무 미완료" (업무, medium, 미완료)
        - "업무 완료"   (업무, high, 완료)
        - "개인 미완료" (개인, low, 미완료)
        - "무분류 완료" (없음, medium, 완료)
    """
    cat1 = await client.post("/api/categories", json={"name": "업무"})
    cat2 = await client.post("/api/categories", json={"name": "개인"})
    cat1_id = cat1.json()["id"]
    cat2_id = cat2.json()["id"]

    t1 = await client.post(
        "/api/todos",
        json={"title": "업무 미완료", "categoryId": cat1_id, "priority": "medium"},
    )
    t2 = await client.post(
        "/api/todos",
        json={"title": "업무 완료", "categoryId": cat1_id, "priority": "high"},
    )
    await client.patch(
        f"/api/todos/{t2.json()['id']}", json={"isCompleted": True}
    )
    t3 = await client.post(
        "/api/todos",
        json={"title": "개인 미완료", "categoryId": cat2_id, "priority": "low"},
    )
    t4 = await client.post(
        "/api/todos",
        json={"title": "무분류 완료", "priority": "medium"},
    )
    await client.patch(
        f"/api/todos/{t4.json()['id']}", json={"isCompleted": True}
    )

    return {
        "cat1_id": cat1_id,
        "cat2_id": cat2_id,
        "todos": {
            "업무 미완료": t1.json(),
            "업무 완료": t2.json(),
            "개인 미완료": t3.json(),
            "무분류 완료": t4.json(),
        },
    }


# ─────────────────────────────────────────────────────────────────
# 1. category_id 필터 검증
# ─────────────────────────────────────────────────────────────────


class TestCategoryIdFilter:
    """category_id 쿼리 파라미터 필터링을 검증한다."""

    async def test_filter_by_category_id(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """category_id로 필터 시 해당 카테고리의 TODO만 반환한다."""
        cat1_id = filter_dataset["cat1_id"]
        response = await client.get(f"/api/todos?category_id={cat1_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        titles = {t["title"] for t in data}
        assert titles == {"업무 미완료", "업무 완료"}

    async def test_filter_by_another_category_id(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """다른 카테고리로 필터 시 올바른 결과를 반환한다."""
        cat2_id = filter_dataset["cat2_id"]
        response = await client.get(f"/api/todos?category_id={cat2_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "개인 미완료"

    async def test_filter_by_nonexistent_category_id(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """존재하지 않는 category_id로 필터 시 빈 결과를 반환한다."""
        response = await client.get("/api/todos?category_id=99999")
        assert response.status_code == 200
        assert response.json() == []


# ─────────────────────────────────────────────────────────────────
# 2. is_completed 필터 검증
# ─────────────────────────────────────────────────────────────────


class TestIsCompletedFilter:
    """is_completed 쿼리 파라미터 필터링을 검증한다."""

    async def test_filter_completed_true(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """is_completed=true로 필터 시 완료된 TODO만 반환한다."""
        response = await client.get("/api/todos?is_completed=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        titles = {t["title"] for t in data}
        assert titles == {"업무 완료", "무분류 완료"}
        for todo in data:
            assert todo["is_completed"] is True

    async def test_filter_completed_false(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """is_completed=false로 필터 시 미완료 TODO만 반환한다."""
        response = await client.get("/api/todos?is_completed=false")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        titles = {t["title"] for t in data}
        assert titles == {"업무 미완료", "개인 미완료"}
        for todo in data:
            assert todo["is_completed"] is False


# ─────────────────────────────────────────────────────────────────
# 3. priority 필터 검증
# ─────────────────────────────────────────────────────────────────


class TestPriorityFilter:
    """priority 쿼리 파라미터 필터링을 검증한다."""

    async def test_filter_by_priority_high(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """priority=high로 필터 시 해당 우선순위만 반환한다."""
        response = await client.get("/api/todos?priority=high")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "업무 완료"
        assert data[0]["priority"] == "high"

    async def test_filter_by_priority_low(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """priority=low로 필터 시 해당 우선순위만 반환한다."""
        response = await client.get("/api/todos?priority=low")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "개인 미완료"

    async def test_filter_by_priority_medium(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """priority=medium으로 필터 시 해당 우선순위만 반환한다."""
        response = await client.get("/api/todos?priority=medium")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        titles = {t["title"] for t in data}
        assert titles == {"업무 미완료", "무분류 완료"}

    async def test_filter_by_invalid_priority(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """유효하지 않은 priority 값으로 필터 시 422를 반환한다."""
        response = await client.get("/api/todos?priority=urgent")
        assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────
# 4. 복합 필터 조합
# ─────────────────────────────────────────────────────────────────


class TestCombinedFilters:
    """여러 쿼리 파라미터를 조합한 필터를 검증한다."""

    async def test_category_and_completed(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """category_id + is_completed 조합 필터가 동작하는지 확인한다."""
        cat1_id = filter_dataset["cat1_id"]
        response = await client.get(
            f"/api/todos?category_id={cat1_id}&is_completed=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "업무 완료"

    async def test_category_and_priority(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """category_id + priority 조합 필터가 동작하는지 확인한다."""
        cat1_id = filter_dataset["cat1_id"]
        response = await client.get(
            f"/api/todos?category_id={cat1_id}&priority=medium"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "업무 미완료"

    async def test_priority_and_completed(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """priority + is_completed 조합 필터가 동작하는지 확인한다."""
        response = await client.get(
            "/api/todos?priority=medium&is_completed=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "무분류 완료"

    async def test_all_three_filters(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """category_id + priority + is_completed 세 가지 조합 필터를 확인한다."""
        cat1_id = filter_dataset["cat1_id"]
        response = await client.get(
            f"/api/todos?category_id={cat1_id}&priority=high&is_completed=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "업무 완료"

    async def test_all_three_filters_no_match(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """세 가지 필터 조합으로 매칭되는 결과가 없으면 빈 리스트를 반환한다."""
        cat1_id = filter_dataset["cat1_id"]
        response = await client.get(
            f"/api/todos?category_id={cat1_id}&priority=low&is_completed=true"
        )
        assert response.status_code == 200
        assert response.json() == []


# ─────────────────────────────────────────────────────────────────
# 5. 필터 미지정 시 전체 반환
# ─────────────────────────────────────────────────────────────────


class TestNoFilter:
    """필터 파라미터 없이 요청 시 전체 TODO를 반환하는지 검증한다."""

    async def test_no_filter_returns_all(
        self, client: AsyncClient, filter_dataset: dict
    ):
        """필터 없이 GET /api/todos 요청 시 전체 4건이 반환된다."""
        response = await client.get("/api/todos")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4


# ─────────────────────────────────────────────────────────────────
# 6. 쿼리 파라미터 엣지 케이스
# ─────────────────────────────────────────────────────────────────


class TestQueryParameterEdgeCases:
    """쿼리 파라미터 관련 엣지 케이스를 검증한다."""

    async def test_unknown_query_param_ignored(self, client: AsyncClient):
        """알 수 없는 쿼리 파라미터는 무시되고 정상 응답한다."""
        await client.post("/api/todos", json={"title": "테스트"})
        response = await client.get("/api/todos?unknown_param=value")
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_category_id_non_integer(self, client: AsyncClient):
        """category_id에 정수가 아닌 값을 전달하면 422를 반환한다."""
        response = await client.get("/api/todos?category_id=abc")
        assert response.status_code == 422

    async def test_is_completed_non_boolean(self, client: AsyncClient):
        """is_completed에 부울이 아닌 값을 전달하면 422를 반환한다."""
        response = await client.get("/api/todos?is_completed=maybe")
        assert response.status_code == 422
