"""TODO CRUD 엔드포인트."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.models import Priority, TodoCreate, TodoResponse, TodoUpdate
from db.queries import (
    create_todo,
    delete_todo,
    get_tags_by_todo_id,
    get_todos,
    set_todo_tags,
    update_todo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/todos", tags=["todos"])


async def _build_response(todo_row: dict) -> TodoResponse:
    """TODO 딕셔너리에 태그를 붙여서 TodoResponse를 만든다."""
    tags = await get_tags_by_todo_id(todo_row["id"])
    return TodoResponse.from_row(todo_row, tags)


@router.get("", response_model=list[TodoResponse])
async def list_todos(
    category_id: Optional[int] = Query(default=None, description="카테고리 ID 필터"),
    priority: Optional[Priority] = Query(default=None, description="우선순위 필터"),
    is_completed: Optional[bool] = Query(
        default=None, description="완료 여부 필터"
    ),
) -> list[TodoResponse]:
    """할 일 목록을 조회한다.

    Args:
        category_id: 카테고리 ID 필터.
        priority: 우선순위 필터.
        is_completed: 완료 여부 필터.

    Returns:
        TODO 응답 리스트.
    """
    rows = await get_todos(
        category_id=category_id,
        priority=priority.value if priority else None,
        is_completed=is_completed,
    )
    return [await _build_response(row) for row in rows]


@router.post("", response_model=TodoResponse, status_code=201)
async def add_todo(body: TodoCreate) -> TodoResponse:
    """새 할 일을 추가한다.

    Args:
        body: 할 일 생성 요청.

    Returns:
        생성된 TODO 응답.
    """
    row = await create_todo(
        title=body.title,
        description=body.description,
        priority=body.priority.value,
        category_id=body.category_id,
        due_date=str(body.due_date) if body.due_date else None,
    )

    # 태그 연결
    if body.tag_ids:
        await set_todo_tags(row["id"], body.tag_ids)

    return await _build_response(row)


@router.patch("/{todo_id}", response_model=TodoResponse)
async def modify_todo(todo_id: int, body: TodoUpdate) -> TodoResponse:
    """할 일을 수정한다 (부분 업데이트).

    Args:
        todo_id: 수정할 TODO ID.
        body: 수정할 필드들.

    Returns:
        수정된 TODO 응답.

    Raises:
        HTTPException: 해당 ID의 TODO가 없을 때 404.
    """
    # tag_ids는 별도 처리하므로 분리
    update_data = body.model_dump(exclude_unset=True)
    tag_ids = update_data.pop("tag_ids", None)

    # TODO 필드 업데이트
    if update_data:
        # Enum 값을 문자열로 변환
        if "priority" in update_data and update_data["priority"] is not None:
            update_data["priority"] = update_data["priority"].value
        # date를 문자열로 변환
        if "due_date" in update_data and update_data["due_date"] is not None:
            update_data["due_date"] = str(update_data["due_date"])

        row = await update_todo(todo_id, **update_data)
    else:
        # 업데이트 필드 없이 태그만 변경하는 경우, 기존 데이터 확인
        from db.connection import get_db

        db = await get_db()
        cursor = await db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
        r = await cursor.fetchone()
        row = dict(r) if r else None

    if row is None:
        raise HTTPException(status_code=404, detail="해당 TODO를 찾을 수 없습니다")

    # 태그 교체
    if tag_ids is not None:
        await set_todo_tags(todo_id, tag_ids)

    return await _build_response(row)


@router.delete("/{todo_id}", status_code=200)
async def remove_todo(todo_id: int) -> dict:
    """할 일을 삭제한다.

    Args:
        todo_id: 삭제할 TODO ID.

    Returns:
        삭제 결과 메시지.

    Raises:
        HTTPException: 해당 ID의 TODO가 없을 때 404.
    """
    deleted = await delete_todo(todo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="해당 TODO를 찾을 수 없습니다")
    return {"message": "삭제 완료", "id": todo_id}
