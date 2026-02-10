"""BUG-003 수정 검증 테스트 — 도현 작성

정렬 안정성 검증:
- BUG-003: ORDER BY created_at DESC만으로는 동일 시각 레코드 순서 미보장
- 수정: ORDER BY created_at DESC, id DESC 로 변경하여 안정적 정렬 보장

검증 항목:
1. 동일 시각에 생성된 TODO가 id DESC 순서로 정렬되는지 확인
2. 서로 다른 시각에 생성된 TODO가 created_at DESC로 정렬되는지 확인
3. 필터 적용 시에도 정렬 순서가 유지되는지 확인
"""

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────
# 동일 시각 레코드 정렬 안정성
# ─────────────────────────────────────────────────────────────────


class TestSameTimestampSorting:
    """동일 created_at 타임스탬프에서 id DESC 정렬을 검증한다."""

    async def test_same_timestamp_records_sorted_by_id_desc(
        self, client: AsyncClient
    ):
        """동일 시각 레코드가 id 내림차순으로 정렬되는지 확인한다.

        DB에 직접 동일 created_at을 설정한 뒤 API 응답 순서를 검증한다.
        """
        from db.connection import get_db

        db = await get_db()

        # 동일 타임스탬프로 여러 레코드를 직접 삽입
        fixed_time = "2026-01-15 10:00:00"
        titles = ["첫 번째", "두 번째", "세 번째", "네 번째", "다섯 번째"]
        inserted_ids = []

        for title in titles:
            cursor = await db.execute(
                """
                INSERT INTO todos (title, priority, created_at, updated_at)
                VALUES (?, 'medium', ?, ?)
                """,
                (title, fixed_time, fixed_time),
            )
            inserted_ids.append(cursor.lastrowid)
        await db.commit()

        resp = await client.get("/api/todos")
        assert resp.status_code == 200

        data = resp.json()
        assert len(data) == 5

        returned_ids = [item["id"] for item in data]
        expected_ids = sorted(inserted_ids, reverse=True)

        assert returned_ids == expected_ids, (
            f"동일 시각 레코드가 id DESC로 정렬되지 않았습니다. "
            f"기대: {expected_ids}, 실제: {returned_ids}"
        )

    async def test_same_timestamp_sorted_by_id_desc_with_many_records(
        self, client: AsyncClient
    ):
        """대량의 동일 시각 레코드에서도 정렬이 안정적인지 확인한다."""
        from db.connection import get_db

        db = await get_db()

        fixed_time = "2026-01-15 10:00:00"
        inserted_ids = []

        for i in range(20):
            cursor = await db.execute(
                """
                INSERT INTO todos (title, priority, created_at, updated_at)
                VALUES (?, 'medium', ?, ?)
                """,
                (f"TODO-{i:03d}", fixed_time, fixed_time),
            )
            inserted_ids.append(cursor.lastrowid)
        await db.commit()

        resp = await client.get("/api/todos")
        assert resp.status_code == 200

        data = resp.json()
        returned_ids = [item["id"] for item in data]
        expected_ids = sorted(inserted_ids, reverse=True)

        assert returned_ids == expected_ids, (
            f"20개 동일 시각 레코드에서 정렬이 불안정합니다. "
            f"기대: {expected_ids}, 실제: {returned_ids}"
        )

    async def test_same_timestamp_title_order_matches_id_desc(
        self, client: AsyncClient
    ):
        """동일 시각 레코드의 제목 순서가 id DESC와 일치하는지 확인한다.

        나중에 삽입된(id가 큰) TODO가 먼저 나와야 한다.
        """
        from db.connection import get_db

        db = await get_db()

        fixed_time = "2026-06-01 12:00:00"
        titles_in_order = ["Alpha", "Beta", "Gamma"]

        for title in titles_in_order:
            await db.execute(
                """
                INSERT INTO todos (title, priority, created_at, updated_at)
                VALUES (?, 'medium', ?, ?)
                """,
                (title, fixed_time, fixed_time),
            )
        await db.commit()

        resp = await client.get("/api/todos")
        assert resp.status_code == 200

        data = resp.json()
        returned_titles = [item["title"] for item in data]

        # id DESC이므로 삽입 역순: Gamma, Beta, Alpha
        assert returned_titles == list(reversed(titles_in_order)), (
            f"제목 순서가 id DESC와 일치하지 않습니다. "
            f"기대: {list(reversed(titles_in_order))}, 실제: {returned_titles}"
        )


# ─────────────────────────────────────────────────────────────────
# 기존 정렬 동작 (created_at DESC) 유지 확인
# ─────────────────────────────────────────────────────────────────


class TestCreatedAtDescSorting:
    """created_at DESC 기본 정렬이 유지되는지 검증한다."""

    async def test_different_timestamps_sorted_by_created_at_desc(
        self, client: AsyncClient
    ):
        """서로 다른 시각의 레코드가 created_at 내림차순으로 정렬되는지 확인한다."""
        from db.connection import get_db

        db = await get_db()

        records = [
            ("오래된 할일", "2026-01-01 09:00:00"),
            ("중간 할일", "2026-01-02 09:00:00"),
            ("최신 할일", "2026-01-03 09:00:00"),
        ]

        for title, ts in records:
            await db.execute(
                """
                INSERT INTO todos (title, priority, created_at, updated_at)
                VALUES (?, 'medium', ?, ?)
                """,
                (title, ts, ts),
            )
        await db.commit()

        resp = await client.get("/api/todos")
        assert resp.status_code == 200

        data = resp.json()
        returned_titles = [item["title"] for item in data]

        assert returned_titles == ["최신 할일", "중간 할일", "오래된 할일"], (
            f"created_at DESC 정렬이 유지되지 않았습니다. "
            f"실제: {returned_titles}"
        )

    async def test_mixed_timestamps_with_same_group(
        self, client: AsyncClient
    ):
        """서로 다른 시각 그룹과 동일 시각 그룹이 섞여있을 때 정렬을 검증한다.

        기대 순서:
        1. 최신 그룹 (같은 시각 → id DESC)
        2. 과거 그룹 (같은 시각 → id DESC)
        """
        from db.connection import get_db

        db = await get_db()

        old_time = "2026-01-01 10:00:00"
        new_time = "2026-01-02 10:00:00"

        old_ids = []
        new_ids = []

        # 과거 그룹 3개
        for title in ["Old-A", "Old-B", "Old-C"]:
            cursor = await db.execute(
                """
                INSERT INTO todos (title, priority, created_at, updated_at)
                VALUES (?, 'medium', ?, ?)
                """,
                (title, old_time, old_time),
            )
            old_ids.append(cursor.lastrowid)

        # 최신 그룹 3개
        for title in ["New-A", "New-B", "New-C"]:
            cursor = await db.execute(
                """
                INSERT INTO todos (title, priority, created_at, updated_at)
                VALUES (?, 'medium', ?, ?)
                """,
                (title, new_time, new_time),
            )
            new_ids.append(cursor.lastrowid)

        await db.commit()

        resp = await client.get("/api/todos")
        assert resp.status_code == 200

        data = resp.json()
        returned_ids = [item["id"] for item in data]

        # 최신 그룹(id DESC) + 과거 그룹(id DESC)
        expected_ids = sorted(new_ids, reverse=True) + sorted(
            old_ids, reverse=True
        )

        assert returned_ids == expected_ids, (
            f"혼합 타임스탬프 정렬이 올바르지 않습니다. "
            f"기대: {expected_ids}, 실제: {returned_ids}"
        )

    async def test_api_created_todos_sorted_newest_first(
        self, client: AsyncClient
    ):
        """API를 통해 순차 생성한 TODO가 최신순으로 정렬되는지 확인한다.

        API로 생성하면 created_at이 자동 설정되므로,
        마지막에 생성된 TODO가 목록 최상단에 나와야 한다.
        """
        titles = ["첫 번째 할일", "두 번째 할일", "세 번째 할일"]
        created_ids = []

        for title in titles:
            resp = await client.post(
                "/api/todos",
                json={"title": title},
            )
            assert resp.status_code == 201
            created_ids.append(resp.json()["id"])

        resp = await client.get("/api/todos")
        assert resp.status_code == 200

        data = resp.json()
        returned_ids = [item["id"] for item in data]

        # API로 순차 생성 시 id가 증가하므로, id DESC면 역순
        expected_ids = list(reversed(created_ids))
        assert returned_ids == expected_ids, (
            f"API 생성 TODO의 정렬이 최신순이 아닙니다. "
            f"기대: {expected_ids}, 실제: {returned_ids}"
        )


# ─────────────────────────────────────────────────────────────────
# 필터 적용 시 정렬 유지
# ─────────────────────────────────────────────────────────────────


class TestSortingWithFilters:
    """필터를 적용해도 정렬 순서가 유지되는지 검증한다."""

    async def test_priority_filter_preserves_sort_order(
        self, client: AsyncClient
    ):
        """우선순위 필터 적용 시에도 동일 시각 정렬이 유지되는지 확인한다."""
        from db.connection import get_db

        db = await get_db()

        fixed_time = "2026-03-01 10:00:00"
        high_ids = []

        # high 우선순위 3개 (동일 시각)
        for title in ["High-A", "High-B", "High-C"]:
            cursor = await db.execute(
                """
                INSERT INTO todos (title, priority, created_at, updated_at)
                VALUES (?, 'high', ?, ?)
                """,
                (title, fixed_time, fixed_time),
            )
            high_ids.append(cursor.lastrowid)

        # low 우선순위 2개 (노이즈)
        for title in ["Low-A", "Low-B"]:
            await db.execute(
                """
                INSERT INTO todos (title, priority, created_at, updated_at)
                VALUES (?, 'low', ?, ?)
                """,
                (title, fixed_time, fixed_time),
            )

        await db.commit()

        resp = await client.get("/api/todos", params={"priority": "high"})
        assert resp.status_code == 200

        data = resp.json()
        assert len(data) == 3

        returned_ids = [item["id"] for item in data]
        expected_ids = sorted(high_ids, reverse=True)

        assert returned_ids == expected_ids, (
            f"우선순위 필터 시 정렬이 올바르지 않습니다. "
            f"기대: {expected_ids}, 실제: {returned_ids}"
        )

    async def test_completion_filter_preserves_sort_order(
        self, client: AsyncClient
    ):
        """완료 여부 필터 적용 시에도 정렬이 유지되는지 확인한다."""
        from db.connection import get_db

        db = await get_db()

        fixed_time = "2026-03-01 10:00:00"
        completed_ids = []

        for title in ["Done-A", "Done-B", "Done-C"]:
            cursor = await db.execute(
                """
                INSERT INTO todos (title, priority, is_completed, created_at, updated_at)
                VALUES (?, 'medium', 1, ?, ?)
                """,
                (title, fixed_time, fixed_time),
            )
            completed_ids.append(cursor.lastrowid)

        # 미완료 2개 (노이즈)
        for title in ["Pending-A", "Pending-B"]:
            await db.execute(
                """
                INSERT INTO todos (title, priority, is_completed, created_at, updated_at)
                VALUES (?, 'medium', 0, ?, ?)
                """,
                (title, fixed_time, fixed_time),
            )

        await db.commit()

        resp = await client.get(
            "/api/todos", params={"is_completed": "true"}
        )
        assert resp.status_code == 200

        data = resp.json()
        assert len(data) == 3

        returned_ids = [item["id"] for item in data]
        expected_ids = sorted(completed_ids, reverse=True)

        assert returned_ids == expected_ids, (
            f"완료 필터 시 정렬이 올바르지 않습니다. "
            f"기대: {expected_ids}, 실제: {returned_ids}"
        )

    async def test_category_filter_preserves_sort_order(
        self, client: AsyncClient
    ):
        """카테고리 필터 적용 시에도 정렬이 유지되는지 확인한다."""
        # 카테고리 생성
        cat_resp = await client.post(
            "/api/categories", json={"name": "업무"}
        )
        assert cat_resp.status_code == 201
        cat_id = cat_resp.json()["id"]

        from db.connection import get_db

        db = await get_db()

        fixed_time = "2026-03-01 10:00:00"
        cat_ids = []

        for title in ["Cat-A", "Cat-B", "Cat-C"]:
            cursor = await db.execute(
                """
                INSERT INTO todos (title, priority, category_id, created_at, updated_at)
                VALUES (?, 'medium', ?, ?, ?)
                """,
                (title, cat_id, fixed_time, fixed_time),
            )
            cat_ids.append(cursor.lastrowid)

        # 카테고리 없는 레코드 (노이즈)
        await db.execute(
            """
            INSERT INTO todos (title, priority, created_at, updated_at)
            VALUES (?, 'medium', ?, ?)
            """,
            ("No-Cat", fixed_time, fixed_time),
        )
        await db.commit()

        resp = await client.get(
            "/api/todos", params={"category_id": cat_id}
        )
        assert resp.status_code == 200

        data = resp.json()
        assert len(data) == 3

        returned_ids = [item["id"] for item in data]
        expected_ids = sorted(cat_ids, reverse=True)

        assert returned_ids == expected_ids, (
            f"카테고리 필터 시 정렬이 올바르지 않습니다. "
            f"기대: {expected_ids}, 실제: {returned_ids}"
        )


# ─────────────────────────────────────────────────────────────────
# SQL 쿼리 직접 검증
# ─────────────────────────────────────────────────────────────────


class TestQueryOrderByClause:
    """get_todos 쿼리의 ORDER BY 절이 올바른지 직접 검증한다."""

    async def test_get_todos_query_includes_id_desc(
        self, client: AsyncClient
    ):
        """get_todos 함수의 쿼리에 id DESC가 포함되어 있는지 소스코드로 확인한다."""
        import inspect
        from db.queries import get_todos

        source = inspect.getsource(get_todos)
        assert "id DESC" in source, (
            "get_todos 쿼리에 'id DESC'가 포함되어 있지 않습니다. "
            "동일 시각 레코드의 정렬 안정성을 보장할 수 없습니다."
        )

    async def test_get_todos_order_by_created_at_before_id(
        self, client: AsyncClient
    ):
        """ORDER BY에서 created_at DESC가 id DESC보다 먼저 선언되어 있는지 확인한다."""
        import inspect
        from db.queries import get_todos

        source = inspect.getsource(get_todos)
        created_at_pos = source.find("created_at DESC")
        id_pos = source.find("id DESC")

        assert created_at_pos != -1, "created_at DESC가 쿼리에 없습니다."
        assert id_pos != -1, "id DESC가 쿼리에 없습니다."
        assert created_at_pos < id_pos, (
            "ORDER BY에서 created_at DESC가 id DESC보다 뒤에 있습니다. "
            "created_at이 1차 정렬 기준이어야 합니다."
        )
