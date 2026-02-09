"""태그 CRUD 엔드포인트."""

import logging

from aiosqlite import IntegrityError
from fastapi import APIRouter, HTTPException

from api.models import TagCreate, TagResponse
from db.queries import create_tag, delete_tag, get_tags

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
async def list_tags() -> list[TagResponse]:
    """태그 목록을 조회한다.

    Returns:
        태그 응답 리스트.
    """
    rows = await get_tags()
    return [TagResponse.from_row(row) for row in rows]


@router.post("", response_model=TagResponse, status_code=201)
async def add_tag(body: TagCreate) -> TagResponse:
    """새 태그를 추가한다.

    Args:
        body: 태그 생성 요청.

    Returns:
        생성된 태그 응답.

    Raises:
        HTTPException: 이미 존재하는 태그 이름일 때 409.
    """
    try:
        row = await create_tag(name=body.name)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=f"이미 존재하는 태그입니다: {body.name}",
        )
    return TagResponse.from_row(row)


@router.delete("/{tag_id}", status_code=204)
async def remove_tag(tag_id: int) -> None:
    """태그를 삭제한다.

    연결된 todo_tags 레코드는 CASCADE 삭제된다.

    Args:
        tag_id: 삭제할 태그 ID.

    Raises:
        HTTPException: 해당 ID의 태그가 없을 때 404.
    """
    deleted = await delete_tag(tag_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="해당 태그를 찾을 수 없습니다")
