// REST API 호출 유틸리티 모듈

const BASE_URL = "/api";

/**
 * 공통 fetch 래퍼 — 응답 상태 확인 및 JSON 파싱 처리.
 * @param {string} url - 요청 URL
 * @param {RequestInit} options - fetch 옵션
 * @returns {Promise<any>} 파싱된 JSON 응답
 */
async function request(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const message = body?.detail ?? `API 오류 (${res.status})`;
    throw new Error(message);
  }

  // 204 No Content 등 빈 응답 처리
  if (res.status === 204) return null;
  return res.json();
}

// ──────────────────────────────────────────────
// TODO API
// ──────────────────────────────────────────────

/**
 * 할 일 목록 조회.
 * @param {Object} [filters] - 필터 옵션
 * @param {number} [filters.categoryId] - 카테고리 ID
 * @param {string} [filters.priority] - 우선순위 (high | medium | low)
 * @param {boolean} [filters.isCompleted] - 완료 여부
 * @returns {Promise<Array>} TODO 목록
 */
export async function fetchTodos(filters = {}) {
  const params = new URLSearchParams();

  if (filters.categoryId != null) {
    params.set("category_id", filters.categoryId);
  }
  if (filters.priority != null) {
    params.set("priority", filters.priority);
  }
  if (filters.isCompleted != null) {
    params.set("is_completed", filters.isCompleted);
  }

  const query = params.toString();
  const url = `${BASE_URL}/todos${query ? `?${query}` : ""}`;
  return request(url);
}

/**
 * 새 할 일 추가.
 * @param {Object} data - 생성 데이터
 * @param {string} data.title - 제목 (필수)
 * @param {string} [data.description] - 상세 설명
 * @param {string} [data.priority] - 우선순위
 * @param {number} [data.categoryId] - 카테고리 ID
 * @param {string} [data.dueDate] - 마감일 (YYYY-MM-DD)
 * @param {number[]} [data.tagIds] - 태그 ID 목록
 * @returns {Promise<Object>} 생성된 TODO
 */
export async function createTodo(data) {
  return request(`${BASE_URL}/todos`, {
    method: "POST",
    body: JSON.stringify({
      title: data.title,
      description: data.description ?? "",
      priority: data.priority ?? "medium",
      category_id: data.categoryId ?? null,
      due_date: data.dueDate ?? null,
      tag_ids: data.tagIds ?? [],
    }),
  });
}

/**
 * 할 일 수정 (부분 업데이트).
 * @param {number} id - TODO ID
 * @param {Object} data - 수정 데이터 (변경할 필드만 포함)
 * @param {string} [data.title] - 제목
 * @param {string} [data.description] - 상세 설명
 * @param {string} [data.priority] - 우선순위
 * @param {boolean} [data.isCompleted] - 완료 여부
 * @param {number} [data.categoryId] - 카테고리 ID
 * @param {string} [data.dueDate] - 마감일 (YYYY-MM-DD)
 * @param {number[]} [data.tagIds] - 태그 ID 목록
 * @returns {Promise<Object>} 수정된 TODO
 */
export async function updateTodo(id, data) {
  // camelCase → snake_case 변환 (백엔드 스펙에 맞춤)
  const body = {};
  if (data.title !== undefined) body.title = data.title;
  if (data.description !== undefined) body.description = data.description;
  if (data.priority !== undefined) body.priority = data.priority;
  if (data.isCompleted !== undefined) body.is_completed = data.isCompleted;
  if (data.categoryId !== undefined) body.category_id = data.categoryId;
  if (data.dueDate !== undefined) body.due_date = data.dueDate;
  if (data.tagIds !== undefined) body.tag_ids = data.tagIds;

  return request(`${BASE_URL}/todos/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

/**
 * 할 일 삭제.
 * @param {number} id - TODO ID
 * @returns {Promise<Object>} 삭제 결과 메시지
 */
export async function deleteTodo(id) {
  return request(`${BASE_URL}/todos/${id}`, { method: "DELETE" });
}

// ──────────────────────────────────────────────
// 카테고리 API
// ──────────────────────────────────────────────

/**
 * 카테고리 목록 조회.
 * @returns {Promise<Array>} 카테고리 목록
 */
export async function fetchCategories() {
  return request(`${BASE_URL}/categories`);
}

/**
 * 새 카테고리 추가.
 * @param {string} name - 카테고리 이름
 * @returns {Promise<Object>} 생성된 카테고리
 */
export async function createCategory(name) {
  return request(`${BASE_URL}/categories`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

/**
 * 카테고리 삭제.
 * @param {number} id - 카테고리 ID
 * @returns {Promise<Object>} 삭제 결과 메시지
 */
export async function deleteCategory(id) {
  return request(`${BASE_URL}/categories/${id}`, { method: "DELETE" });
}

// ──────────────────────────────────────────────
// 태그 API
// ──────────────────────────────────────────────

/**
 * 태그 목록 조회.
 * @returns {Promise<Array>} 태그 목록
 */
export async function fetchTags() {
  return request(`${BASE_URL}/tags`);
}

/**
 * 새 태그 추가.
 * @param {string} name - 태그 이름
 * @returns {Promise<Object>} 생성된 태그
 */
export async function createTag(name) {
  return request(`${BASE_URL}/tags`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}
