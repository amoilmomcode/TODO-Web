"""카테고리 CRUD 엔드포인트."""

import logging

from aiosqlite import IntegrityError
from fastapi import APIRouter, HTTPException

from api.models import CategoryCreate, CategoryResponse
from db.queries import create_category, delete_category, get_categories

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
async def list_categories() -> list[CategoryResponse]:
    """카테고리 목록을 조회한다.

    Returns:
        카테고리 응답 리스트.
    """
    rows = await get_categories()
    return [CategoryResponse.from_row(row) for row in rows]


@router.post("", response_model=CategoryResponse, status_code=201)
async def add_category(body: CategoryCreate) -> CategoryResponse:
    """새 카테고리를 추가한다.

    Args:
        body: 카테고리 생성 요청.

    Returns:
        생성된 카테고리 응답.

    Raises:
        HTTPException: 이미 존재하는 카테고리 이름일 때 409.
    """
    try:
        row = await create_category(name=body.name)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=f"이미 존재하는 카테고리입니다: {body.name}",
        )
    return CategoryResponse.from_row(row)


@router.delete("/{category_id}", status_code=204)
async def remove_category(category_id: int) -> None:
    """카테고리를 삭제한다.

    연결된 TODO의 category_id는 NULL로 변경된다.

    Args:
        category_id: 삭제할 카테고리 ID.

    Raises:
        HTTPException: 해당 ID의 카테고리가 없을 때 404.
    """
    deleted = await delete_category(category_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail="해당 카테고리를 찾을 수 없습니다"
        )
