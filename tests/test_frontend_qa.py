"""
프론트엔드 QA 테스트 — 달력 뷰 및 통합 모달 기능 점검

이 테스트는 다음 항목들을 검증합니다:
- 기본 TODO CRUD 기능
- 통합 모달(추가/수정) 동작
- 달력 뷰 렌더링 및 상호작용
- 뷰 모드 전환 및 저장/복원
- 에지 케이스 (월 경계, 빈 달, 마감일 없는 TODO 등)

주의: 프론트엔드 테스트이므로 Selenium 또는 Playwright 등이 필요합니다.
여기서는 API 및 로직 검증 위주로 작성하고, 실제 브라우저 테스트는 수동 QA로 보완합니다.
"""

import pytest
import pytest_asyncio
from datetime import date, timedelta
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def setup_test_data(client: AsyncClient):
    """
    테스트용 카테고리, 태그, TODO 데이터 생성
    """
    # 카테고리 생성
    cat_resp = await client.post("/api/categories", json={"name": "테스트카테고리"})
    assert cat_resp.status_code == 201
    category_id = cat_resp.json()["id"]

    # 태그 생성
    tag_resp = await client.post("/api/tags", json={"name": "테스트태그"})
    assert tag_resp.status_code == 201
    tag_id = tag_resp.json()["id"]

    # 마감일이 있는 TODO 생성
    today = date.today()
    tomorrow = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)

    todo1 = await client.post(
        "/api/todos",
        json={
            "title": "오늘 마감",
            "description": "오늘 마감인 할일",
            "priority": "high",
            "categoryId": category_id,
            "dueDate": str(today),
            "tagIds": [tag_id],
        },
    )
    assert todo1.status_code == 201

    todo2 = await client.post(
        "/api/todos",
        json={
            "title": "내일 마감",
            "description": "내일 마감인 할일",
            "priority": "medium",
            "dueDate": str(tomorrow),
        },
    )
    assert todo2.status_code == 201

    todo3 = await client.post(
        "/api/todos",
        json={
            "title": "어제 마감 (지남)",
            "description": "어제 마감인 할일",
            "priority": "low",
            "dueDate": str(yesterday),
        },
    )
    assert todo3.status_code == 201

    # 마감일 없는 TODO
    todo4 = await client.post(
        "/api/todos",
        json={
            "title": "마감일 없음",
            "description": "마감일이 설정되지 않은 할일",
            "priority": "medium",
        },
    )
    assert todo4.status_code == 201

    return {
        "category_id": category_id,
        "tag_id": tag_id,
        "todos": [
            todo1.json(),
            todo2.json(),
            todo3.json(),
            todo4.json(),
        ],
    }


# ─────────────────────────────────────────────────────────────────
# 기본 TODO CRUD 테스트
# ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_todo(client, setup_test_data):
    """TODO 추가 기능 테스트"""
    data = setup_test_data
    resp = await client.post(
        "/api/todos",
        json={
            "title": "새 할일",
            "description": "설명",
            "priority": "high",
            "categoryId": data["category_id"],
            "dueDate": str(date.today()),
            "tagIds": [data["tag_id"]],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "새 할일"
    assert body["priority"] == "high"
    assert body["is_completed"] is False


@pytest.mark.asyncio
async def test_update_todo(client, setup_test_data):
    """TODO 수정 기능 테스트"""
    data = setup_test_data
    todo_id = data["todos"][0]["id"]

    resp = await client.patch(
        f"/api/todos/{todo_id}",
        json={"title": "수정된 제목", "priority": "low"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "수정된 제목"
    assert body["priority"] == "low"


@pytest.mark.asyncio
async def test_complete_todo(client, setup_test_data):
    """TODO 완료 처리 테스트"""
    data = setup_test_data
    todo_id = data["todos"][1]["id"]

    resp = await client.patch(
        f"/api/todos/{todo_id}",
        json={"isCompleted": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_completed"] is True


@pytest.mark.asyncio
async def test_delete_todo(client, setup_test_data):
    """TODO 삭제 기능 테스트"""
    data = setup_test_data
    todo_id = data["todos"][2]["id"]

    resp = await client.delete(f"/api/todos/{todo_id}")
    assert resp.status_code == 204

    # 삭제 확인
    resp = await client.get("/api/todos")
    todos = resp.json()
    assert all(t["id"] != todo_id for t in todos)


# ─────────────────────────────────────────────────────────────────
# 달력 뷰 데이터 검증
# ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_calendar_todos_grouping(client, setup_test_data):
    """
    마감일별 TODO 그룹핑 검증
    - 마감일이 있는 TODO만 달력에 표시
    - 마감일 없는 TODO는 달력에 미표시
    """
    resp = await client.get("/api/todos")
    assert resp.status_code == 200
    todos = resp.json()

    # 마감일이 있는 TODO 필터링
    todos_with_due = [t for t in todos if t.get("due_date")]
    assert len(todos_with_due) >= 3

    # 마감일 없는 TODO 존재 확인
    todos_without_due = [t for t in todos if not t.get("due_date")]
    assert len(todos_without_due) >= 1


@pytest.mark.asyncio
async def test_calendar_date_boundaries(client):
    """
    월 경계 케이스 검증
    - 1월 이전 달 → 12월 (연도 -1)
    - 12월 다음 달 → 1월 (연도 +1)
    """
    # 이 테스트는 프론트엔드 로직 검증이므로, 백엔드에서는 API 응답만 확인
    # app.js의 renderCalendar() 로직이 올바른지는 수동 QA로 보완

    # 12월 데이터 생성
    december_date = date(2025, 12, 31)
    resp = await client.post(
        "/api/todos",
        json={
            "title": "12월 31일 할일",
            "dueDate": str(december_date),
        },
    )
    assert resp.status_code == 201

    # 1월 데이터 생성
    january_date = date(2026, 1, 1)
    resp = await client.post(
        "/api/todos",
        json={
            "title": "1월 1일 할일",
            "dueDate": str(january_date),
        },
    )
    assert resp.status_code == 201

    # API 응답 확인
    resp = await client.get("/api/todos")
    todos = resp.json()
    assert any(t["due_date"] == str(december_date) for t in todos)
    assert any(t["due_date"] == str(january_date) for t in todos)


# ─────────────────────────────────────────────────────────────────
# 필터 기능 테스트
# ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_filter_by_category(client, setup_test_data):
    """카테고리 필터 테스트"""
    data = setup_test_data
    resp = await client.get(f"/api/todos?category_id={data['category_id']}")
    assert resp.status_code == 200
    todos = resp.json()
    assert all(t.get("category_id") == data["category_id"] for t in todos)


@pytest.mark.asyncio
async def test_filter_by_priority(client, setup_test_data):
    """우선순위 필터 테스트"""
    resp = await client.get("/api/todos?priority=high")
    assert resp.status_code == 200
    todos = resp.json()
    assert all(t["priority"] == "high" for t in todos)


@pytest.mark.asyncio
async def test_filter_by_completed(client, setup_test_data):
    """완료 여부 필터 테스트"""
    # 일부 완료 처리
    data = setup_test_data
    await client.patch(
        f"/api/todos/{data['todos'][0]['id']}",
        json={"isCompleted": True},
    )

    # 완료된 항목만 필터
    resp = await client.get("/api/todos?is_completed=true")
    assert resp.status_code == 200
    todos = resp.json()
    assert all(t["is_completed"] is True for t in todos)

    # 미완료 항목만 필터
    resp = await client.get("/api/todos?is_completed=false")
    assert resp.status_code == 200
    todos = resp.json()
    assert all(t["is_completed"] is False for t in todos)


# ─────────────────────────────────────────────────────────────────
# 에지 케이스 테스트
# ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_calendar_month(client):
    """빈 달 렌더링 테스트 (데이터 없는 월)"""
    # 미래의 먼 날짜
    future_date = date(2030, 6, 15)
    resp = await client.get("/api/todos")
    todos = resp.json()

    # 해당 월에 마감일이 있는 TODO가 없는지 확인
    future_month_todos = [
        t
        for t in todos
        if t.get("due_date")
        and date.fromisoformat(t["due_date"]).year == 2030
        and date.fromisoformat(t["due_date"]).month == 6
    ]
    assert len(future_month_todos) == 0


@pytest.mark.asyncio
async def test_overdue_todos(client, setup_test_data):
    """
    지난 마감일 TODO 검증
    - 마감일이 오늘보다 이전인 TODO가 강조 표시되는지 확인
    """
    resp = await client.get("/api/todos")
    todos = resp.json()

    # 지난 마감일을 가진 미완료 TODO
    overdue = [
        t
        for t in todos
        if t.get("due_date")
        and date.fromisoformat(t["due_date"]) < date.today()
        and not t["is_completed"]
    ]
    assert len(overdue) >= 1

    # 프론트엔드에서 스타일 적용 확인 (수동 QA)


@pytest.mark.asyncio
async def test_todo_without_optional_fields(client):
    """
    선택적 필드가 없는 TODO 생성 테스트
    - 최소한의 필드(제목)만으로 TODO 생성
    """
    resp = await client.post(
        "/api/todos",
        json={"title": "최소 TODO"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "최소 TODO"
    assert body["priority"] == "medium"  # 기본값
    assert body["is_completed"] is False
    assert body["due_date"] is None


# ─────────────────────────────────────────────────────────────────
# 보안 및 입력 검증 테스트
# ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_xss_prevention_in_title(client):
    """
    XSS 공격 방지 검증
    - 제목에 HTML/JS 코드 삽입 시 이스케이프 처리
    """
    xss_payload = "<script>alert('XSS')</script>"
    resp = await client.post(
        "/api/todos",
        json={"title": xss_payload},
    )
    assert resp.status_code == 201
    body = resp.json()

    # 백엔드는 그대로 저장하지만, 프론트엔드에서 escapeHtml() 처리해야 함
    assert body["title"] == xss_payload

    # 프론트엔드 렌더링 시 이스케이프 확인은 수동 QA


@pytest.mark.asyncio
async def test_invalid_priority(client):
    """
    잘못된 우선순위 값 검증
    - high/medium/low 외의 값 거부
    """
    resp = await client.post(
        "/api/todos",
        json={"title": "잘못된 우선순위", "priority": "invalid"},
    )
    assert resp.status_code in [400, 422]


@pytest.mark.asyncio
async def test_invalid_date_format(client):
    """
    잘못된 날짜 형식 검증
    """
    resp = await client.post(
        "/api/todos",
        json={"title": "잘못된 날짜", "dueDate": "2025-13-40"},
    )
    assert resp.status_code in [400, 422]


# ─────────────────────────────────────────────────────────────────
# 수동 QA 체크리스트 (브라우저 테스트 필요)
# ─────────────────────────────────────────────────────────────────

"""
다음 항목들은 자동화 테스트로 검증하기 어려우므로, 수동 QA가 필요합니다:

1. 모달 애니메이션
   - fade-in/slide-up 효과 확인
   - backdrop transition 확인

2. 달력 뷰 상호작용
   - TODO 클릭 → 수정 모달 열림
   - 날짜 클릭 → 추가 모달 열림 (마감일 자동 세팅)
   - 월 이동 네비게이션 (이전/다음/오늘)

3. 뷰 모드 전환
   - 리스트/달력 뷰 토글
   - localStorage 저장/복원 (페이지 새로고침 후 확인)

4. 모달 닫기
   - ESC 키
   - backdrop 클릭
   - 취소 버튼

5. 달력 렌더링
   - 일요일/토요일 색상 구분
   - 오늘 날짜 하이라이트
   - 이전/다음 달 날짜 회색 처리
   - TODO 3개 이상 시 "+N개 더" 표시

6. 에지 케이스
   - 빈 달 렌더링
   - 월 경계 넘을 때 (12월 → 1월, 1월 → 12월)
   - 마감일 없는 TODO → 달력에 미표시

7. 요일 계산 정확성
   - 이전 달 날짜의 요일 클래스
   - 다음 달 날짜의 요일 클래스

8. XSS 방어
   - 제목/설명에 HTML 태그 입력 시 이스케이프 확인
"""
