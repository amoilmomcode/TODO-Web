"""API 요청/응답 Pydantic 모델 정의."""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Priority(str, Enum):
    """할 일 우선순위."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ──────────────────────────────────────────────
# TODO 모델
# ──────────────────────────────────────────────


class TodoCreate(BaseModel):
    """할 일 생성 요청 모델.

    camelCase alias를 지원하여 프론트엔드에서 categoryId 등으로
    요청해도 정상 처리된다.

    Attributes:
        title: 할 일 제목 (필수, 1~200자).
        description: 상세 설명.
        priority: 우선순위 (high/medium/low).
        category_id: 카테고리 ID.
        due_date: 마감일.
        tag_ids: 연결할 태그 ID 목록.
    """

    model_config = {"populate_by_name": True}

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    priority: Priority = Field(default=Priority.MEDIUM)
    category_id: Optional[int] = Field(default=None, alias="categoryId")
    due_date: Optional[date] = Field(default=None, alias="dueDate")
    tag_ids: list[int] = Field(default_factory=list, alias="tagIds")


class TodoUpdate(BaseModel):
    """할 일 수정 요청 모델 (PATCH용, 모두 Optional).

    camelCase alias를 지원하여 프론트엔드에서 isCompleted 등으로
    요청해도 정상 처리된다.

    Attributes:
        title: 할 일 제목 (1~200자).
        description: 상세 설명.
        priority: 우선순위 (high/medium/low).
        is_completed: 완료 여부.
        category_id: 카테고리 ID.
        due_date: 마감일.
        tag_ids: 연결할 태그 ID 목록.
    """

    model_config = {"populate_by_name": True}

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    priority: Optional[Priority] = Field(default=None)
    is_completed: Optional[bool] = Field(
        default=None, alias="isCompleted"
    )
    category_id: Optional[int] = Field(
        default=None, alias="categoryId"
    )
    due_date: Optional[date] = Field(
        default=None, alias="dueDate"
    )
    tag_ids: Optional[list[int]] = Field(
        default=None, alias="tagIds"
    )


class TagResponse(BaseModel):
    """태그 응답 모델.

    Attributes:
        id: 태그 ID.
        name: 태그 이름.
    """

    id: int
    name: str

    @classmethod
    def from_row(cls, row: dict) -> "TagResponse":
        """DB 행 dict에서 TagResponse 생성.

        Args:
            row: DB 쿼리 결과 dict (id, name 포함).

        Returns:
            TagResponse 인스턴스.
        """
        return cls(id=row["id"], name=row["name"])


class TodoResponse(BaseModel):
    """할 일 응답 모델.

    Attributes:
        id: 할 일 ID.
        title: 할 일 제목.
        description: 상세 설명.
        priority: 우선순위.
        is_completed: 완료 여부.
        category_id: 카테고리 ID.
        due_date: 마감일.
        tags: 연결된 태그 목록.
        created_at: 생성 시각.
        updated_at: 수정 시각.
    """

    id: int
    title: str
    description: str
    priority: Priority
    is_completed: bool
    category_id: Optional[int]
    due_date: Optional[date]
    tags: list[TagResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: dict, tags: Optional[list[dict]] = None) -> "TodoResponse":
        """DB 행 dict에서 TodoResponse 생성.

        Args:
            row: todos 테이블 쿼리 결과 dict.
            tags: 해당 todo에 연결된 태그 dict 목록.

        Returns:
            TodoResponse 인스턴스.
        """
        return cls(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            priority=row["priority"],
            is_completed=bool(row["is_completed"]),
            category_id=row["category_id"],
            due_date=row["due_date"],
            tags=[TagResponse.from_row(t) for t in (tags or [])],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


# ──────────────────────────────────────────────
# 카테고리 모델
# ──────────────────────────────────────────────


class CategoryCreate(BaseModel):
    """카테고리 생성 요청 모델.

    Attributes:
        name: 카테고리 이름 (필수, 1~50자).
    """

    name: str = Field(..., min_length=1, max_length=50)


class CategoryResponse(BaseModel):
    """카테고리 응답 모델.

    Attributes:
        id: 카테고리 ID.
        name: 카테고리 이름.
        created_at: 생성 시각.
    """

    id: int
    name: str
    created_at: datetime

    @classmethod
    def from_row(cls, row: dict) -> "CategoryResponse":
        """DB 행 dict에서 CategoryResponse 생성.

        Args:
            row: categories 테이블 쿼리 결과 dict.

        Returns:
            CategoryResponse 인스턴스.
        """
        return cls(id=row["id"], name=row["name"], created_at=row["created_at"])


# ──────────────────────────────────────────────
# 태그 모델 (Create는 여기, Response는 위에 정의됨)
# ──────────────────────────────────────────────


class TagCreate(BaseModel):
    """태그 생성 요청 모델.

    Attributes:
        name: 태그 이름 (필수, 1~30자).
    """

    name: str = Field(..., min_length=1, max_length=30)
