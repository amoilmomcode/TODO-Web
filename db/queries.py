"""SQL 쿼리 함수 모듈.

모든 CRUD 작업을 위한 데이터 액세스 함수를 제공한다.
파라미터 바인딩을 사용하여 SQL Injection을 방지한다.
"""

import logging
from typing import Any

from db.connection import get_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TODO 관련
# ---------------------------------------------------------------------------


async def get_todos(
    *,
    category_id: int | None = None,
    priority: str | None = None,
    is_completed: bool | None = None,
) -> list[dict[str, Any]]:
    """TODO 목록을 조회한다.

    Args:
        category_id: 카테고리 ID 필터.
        priority: 우선순위 필터 ('high', 'medium', 'low').
        is_completed: 완료 여부 필터.

    Returns:
        TODO 딕셔너리 리스트.
    """
    db = await get_db()

    query = "SELECT * FROM todos WHERE 1=1"
    params: list[Any] = []

    if category_id is not None:
        query += " AND category_id = ?"
        params.append(category_id)
    if priority is not None:
        query += " AND priority = ?"
        params.append(priority)
    if is_completed is not None:
        query += " AND is_completed = ?"
        params.append(is_completed)

    query += " ORDER BY created_at DESC"

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def create_todo(
    *,
    title: str,
    description: str = "",
    priority: str = "medium",
    category_id: int | None = None,
    due_date: str | None = None,
) -> dict[str, Any]:
    """새 TODO를 생성한다.

    Args:
        title: 할 일 제목.
        description: 상세 설명.
        priority: 우선순위 ('high', 'medium', 'low').
        category_id: 카테고리 ID.
        due_date: 마감일 (YYYY-MM-DD).

    Returns:
        생성된 TODO 딕셔너리.
    """
    db = await get_db()

    cursor = await db.execute(
        """
        INSERT INTO todos (title, description, priority, category_id, due_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title, description, priority, category_id, due_date),
    )
    await db.commit()

    row_id = cursor.lastrowid
    logger.info("TODO 생성 완료: id=%s, title=%s", row_id, title)

    cursor = await db.execute("SELECT * FROM todos WHERE id = ?", (row_id,))
    row = await cursor.fetchone()
    return dict(row)  # type: ignore[arg-type]


async def update_todo(todo_id: int, **data: Any) -> dict[str, Any] | None:
    """TODO를 수정한다.

    Args:
        todo_id: 수정할 TODO ID.
        **data: 수정할 필드와 값. 허용 필드:
            title, description, priority, is_completed, category_id, due_date.

    Returns:
        수정된 TODO 딕셔너리. 해당 ID가 없으면 None.
    """
    allowed_fields = {
        "title",
        "description",
        "priority",
        "is_completed",
        "category_id",
        "due_date",
    }
    # 허용되지 않는 필드 필터링
    fields = {k: v for k, v in data.items() if k in allowed_fields}
    if not fields:
        logger.warning("update_todo 호출 시 유효한 필드 없음: id=%s", todo_id)
        return None

    db = await get_db()

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [todo_id]

    await db.execute(
        f"UPDATE todos SET {set_clause} WHERE id = ?",  # noqa: S608
        params,
    )
    await db.commit()
    logger.info("TODO 수정 완료: id=%s, fields=%s", todo_id, list(fields.keys()))

    cursor = await db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def delete_todo(todo_id: int) -> bool:
    """TODO를 삭제한다.

    Args:
        todo_id: 삭제할 TODO ID.

    Returns:
        삭제 성공 여부. 해당 ID가 없으면 False.
    """
    db = await get_db()

    cursor = await db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    await db.commit()

    deleted = cursor.rowcount > 0
    if deleted:
        logger.info("TODO 삭제 완료: id=%s", todo_id)
    else:
        logger.warning("삭제할 TODO를 찾지 못함: id=%s", todo_id)
    return deleted


# ---------------------------------------------------------------------------
# 카테고리 관련
# ---------------------------------------------------------------------------


async def get_categories() -> list[dict[str, Any]]:
    """카테고리 목록을 조회한다.

    Returns:
        카테고리 딕셔너리 리스트.
    """
    db = await get_db()
    cursor = await db.execute("SELECT * FROM categories ORDER BY name")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def create_category(name: str) -> dict[str, Any]:
    """새 카테고리를 생성한다.

    Args:
        name: 카테고리 이름.

    Returns:
        생성된 카테고리 딕셔너리.

    Raises:
        aiosqlite.IntegrityError: 이미 존재하는 카테고리 이름인 경우.
    """
    db = await get_db()

    cursor = await db.execute(
        "INSERT INTO categories (name) VALUES (?)",
        (name,),
    )
    await db.commit()

    row_id = cursor.lastrowid
    logger.info("카테고리 생성 완료: id=%s, name=%s", row_id, name)

    cursor = await db.execute("SELECT * FROM categories WHERE id = ?", (row_id,))
    row = await cursor.fetchone()
    return dict(row)  # type: ignore[arg-type]


async def delete_category(category_id: int) -> bool:
    """카테고리를 삭제한다.

    연결된 TODO의 category_id는 ON DELETE SET NULL에 의해 NULL로 설정된다.

    Args:
        category_id: 삭제할 카테고리 ID.

    Returns:
        삭제 성공 여부.
    """
    db = await get_db()

    cursor = await db.execute(
        "DELETE FROM categories WHERE id = ?",
        (category_id,),
    )
    await db.commit()

    deleted = cursor.rowcount > 0
    if deleted:
        logger.info("카테고리 삭제 완료: id=%s", category_id)
    else:
        logger.warning("삭제할 카테고리를 찾지 못함: id=%s", category_id)
    return deleted


# ---------------------------------------------------------------------------
# 태그 관련
# ---------------------------------------------------------------------------


async def get_tags() -> list[dict[str, Any]]:
    """태그 목록을 조회한다.

    Returns:
        태그 딕셔너리 리스트.
    """
    db = await get_db()
    cursor = await db.execute("SELECT * FROM tags ORDER BY name")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def create_tag(name: str) -> dict[str, Any]:
    """새 태그를 생성한다.

    Args:
        name: 태그 이름.

    Returns:
        생성된 태그 딕셔너리.

    Raises:
        aiosqlite.IntegrityError: 이미 존재하는 태그 이름인 경우.
    """
    db = await get_db()

    cursor = await db.execute(
        "INSERT INTO tags (name) VALUES (?)",
        (name,),
    )
    await db.commit()

    row_id = cursor.lastrowid
    logger.info("태그 생성 완료: id=%s, name=%s", row_id, name)

    cursor = await db.execute("SELECT * FROM tags WHERE id = ?", (row_id,))
    row = await cursor.fetchone()
    return dict(row)  # type: ignore[arg-type]


async def get_tags_by_todo_id(todo_id: int) -> list[dict[str, Any]]:
    """특정 TODO에 연결된 태그 목록을 조회한다.

    Args:
        todo_id: TODO ID.

    Returns:
        태그 딕셔너리 리스트.
    """
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT t.id, t.name
        FROM tags t
        JOIN todo_tags tt ON t.id = tt.tag_id
        WHERE tt.todo_id = ?
        ORDER BY t.name
        """,
        (todo_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def set_todo_tags(todo_id: int, tag_ids: list[int]) -> None:
    """TODO의 태그를 일괄 교체한다.

    기존 연결을 모두 삭제한 뒤 새 태그들을 연결한다.

    Args:
        todo_id: TODO ID.
        tag_ids: 연결할 태그 ID 목록.
    """
    db = await get_db()
    await db.execute("DELETE FROM todo_tags WHERE todo_id = ?", (todo_id,))
    for tag_id in tag_ids:
        await db.execute(
            "INSERT INTO todo_tags (todo_id, tag_id) VALUES (?, ?)",
            (todo_id, tag_id),
        )
    await db.commit()
    logger.info("TODO 태그 일괄 교체: todo_id=%s, tag_ids=%s", todo_id, tag_ids)


async def add_todo_tag(todo_id: int, tag_id: int) -> bool:
    """TODO에 태그를 연결한다.

    Args:
        todo_id: TODO ID.
        tag_id: 태그 ID.

    Returns:
        연결 성공 여부.

    Raises:
        aiosqlite.IntegrityError: 이미 연결되어 있거나, 유효하지 않은 ID인 경우.
    """
    db = await get_db()

    await db.execute(
        "INSERT INTO todo_tags (todo_id, tag_id) VALUES (?, ?)",
        (todo_id, tag_id),
    )
    await db.commit()
    logger.info("TODO-태그 연결 완료: todo_id=%s, tag_id=%s", todo_id, tag_id)
    return True


async def remove_todo_tag(todo_id: int, tag_id: int) -> bool:
    """TODO에서 태그를 제거한다.

    Args:
        todo_id: TODO ID.
        tag_id: 태그 ID.

    Returns:
        제거 성공 여부. 연결이 없으면 False.
    """
    db = await get_db()

    cursor = await db.execute(
        "DELETE FROM todo_tags WHERE todo_id = ? AND tag_id = ?",
        (todo_id, tag_id),
    )
    await db.commit()

    deleted = cursor.rowcount > 0
    if deleted:
        logger.info("TODO-태그 제거 완료: todo_id=%s, tag_id=%s", todo_id, tag_id)
    else:
        logger.warning(
            "제거할 TODO-태그 연결을 찾지 못함: todo_id=%s, tag_id=%s",
            todo_id,
            tag_id,
        )
    return deleted
