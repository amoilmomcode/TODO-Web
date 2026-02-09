// 메인 앱 로직 — DOM 조작 & 이벤트 처리

import {
  fetchTodos,
  createTodo,
  updateTodo,
  deleteTodo,
  fetchCategories,
  createCategory,
  deleteCategory,
  fetchTags,
  createTag,
} from "./api.js";

// ──────────────────────────────────────────────
// DOM 요소 캐싱
// ──────────────────────────────────────────────

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// 필터
const filterCategory = $("#filter-category");
const filterPriority = $("#filter-priority");
const filterCompleted = $("#filter-completed");
const btnApplyFilter = $("#btn-apply-filter");
const btnResetFilter = $("#btn-reset-filter");

// 카테고리 관리
const formAddCategory = $("#form-add-category");
const inputCategoryName = $("#input-category-name");
const categoryList = $("#category-list");

// 태그 관리
const formAddTag = $("#form-add-tag");
const inputTagName = $("#input-tag-name");
const tagList = $("#tag-list");

// TODO 추가 폼
const formAddTodo = $("#form-add-todo");
const inputTodoTitle = $("#input-todo-title");
const inputTodoDescription = $("#input-todo-description");
const selectTodoPriority = $("#select-todo-priority");
const selectTodoCategory = $("#select-todo-category");
const inputTodoDueDate = $("#input-todo-due-date");
const selectTodoTags = $("#select-todo-tags");

// TODO 목록
const todoListEl = $("#todo-list");
const todoCount = $("#todo-count");
const todoEmptyMessage = $("#todo-empty-message");

// 수정 모달
const modalEditTodo = $("#modal-edit-todo");
const formEditTodo = $("#form-edit-todo");
const editTodoId = $("#edit-todo-id");
const editTodoTitle = $("#edit-todo-title");
const editTodoDescription = $("#edit-todo-description");
const editTodoPriority = $("#edit-todo-priority");
const editTodoCategory = $("#edit-todo-category");
const editTodoDueDate = $("#edit-todo-due-date");
const editTodoTags = $("#edit-todo-tags");
const btnCancelEdit = $("#btn-cancel-edit");

// ──────────────────────────────────────────────
// 상태
// ──────────────────────────────────────────────

let categories = [];
let tags = [];

// ──────────────────────────────────────────────
// 유틸리티
// ──────────────────────────────────────────────

const PRIORITY_LABELS = { high: "높음", medium: "보통", low: "낮음" };

/** 날짜 문자열을 보기 좋게 포맷한다. */
function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** 토스트 메시지를 화면에 표시한다. */
function showToast(message, type = "info") {
  let container = $("#toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.style.cssText =
      "position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  const colors = {
    info: "#4a90d9",
    success: "#28a745",
    error: "#dc3545",
    warning: "#fd7e14",
  };
  toast.textContent = message;
  toast.style.cssText = `
    padding:12px 20px;background:${colors[type] || colors.info};color:#fff;
    border-radius:6px;font-size:0.9rem;box-shadow:0 4px 12px rgba(0,0,0,0.15);
    opacity:0;transform:translateX(40px);transition:all 0.3s ease;
  `;
  container.appendChild(toast);

  // 등장 애니메이션
  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateX(0)";
  });

  // 3초 후 자동 제거
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(40px)";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

/** API 호출을 감싸서 에러를 토스트로 표시한다. */
async function withErrorHandling(fn, errorMsg = "작업 중 오류가 발생했습니다") {
  try {
    return await fn();
  } catch (err) {
    console.error(err);
    showToast(err.message || errorMsg, "error");
    return null;
  }
}

// ──────────────────────────────────────────────
// 카테고리 / 태그 로딩 + 셀렉트 업데이트
// ──────────────────────────────────────────────

/** 카테고리 목록을 로드하고 관련 UI를 모두 갱신한다. */
async function loadCategories() {
  const data = await withErrorHandling(fetchCategories, "카테고리를 불러올 수 없습니다");
  if (!data) return;
  categories = data;
  renderCategoryList();
  updateCategorySelects();
}

/** 태그 목록을 로드하고 관련 UI를 모두 갱신한다. */
async function loadTags() {
  const data = await withErrorHandling(fetchTags, "태그를 불러올 수 없습니다");
  if (!data) return;
  tags = data;
  renderTagList();
  updateTagSelects();
}

/** 카테고리 셀렉트 박스들을 갱신한다. */
function updateCategorySelects() {
  const selects = [filterCategory, selectTodoCategory, editTodoCategory];
  for (const sel of selects) {
    const currentVal = sel.value;
    // 첫 번째 옵션(전체/없음) 유지
    const firstOption = sel.options[0];
    sel.innerHTML = "";
    sel.appendChild(firstOption);
    for (const cat of categories) {
      const opt = document.createElement("option");
      opt.value = cat.id;
      opt.textContent = cat.name;
      sel.appendChild(opt);
    }
    // 기존 선택값 복원
    sel.value = currentVal;
  }
}

/** 태그 멀티셀렉트 박스들을 갱신한다. */
function updateTagSelects() {
  const selects = [selectTodoTags, editTodoTags];
  for (const sel of selects) {
    // 기존 선택된 값 저장
    const selectedValues = Array.from(sel.selectedOptions).map((o) => o.value);
    sel.innerHTML = "";
    for (const tag of tags) {
      const opt = document.createElement("option");
      opt.value = tag.id;
      opt.textContent = tag.name;
      if (selectedValues.includes(String(tag.id))) {
        opt.selected = true;
      }
      sel.appendChild(opt);
    }
  }
}

/** 사이드바 카테고리 목록을 렌더링한다. */
function renderCategoryList() {
  categoryList.innerHTML = "";
  if (categories.length === 0) {
    categoryList.innerHTML = '<li class="empty-hint">카테고리 없음</li>';
    return;
  }
  for (const cat of categories) {
    const li = document.createElement("li");
    li.innerHTML = `
      <span>${escapeHtml(cat.name)}</span>
      <button type="button" class="btn-delete-item" data-id="${cat.id}" title="삭제">✕</button>
    `;
    categoryList.appendChild(li);
  }
}

/** 사이드바 태그 목록을 렌더링한다. */
function renderTagList() {
  tagList.innerHTML = "";
  if (tags.length === 0) {
    tagList.innerHTML = '<li class="empty-hint">태그 없음</li>';
    return;
  }
  for (const tag of tags) {
    const li = document.createElement("li");
    li.innerHTML = `
      <span>${escapeHtml(tag.name)}</span>
    `;
    tagList.appendChild(li);
  }
}

/** HTML 이스케이프 처리. */
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ──────────────────────────────────────────────
// TODO 목록 렌더링
// ──────────────────────────────────────────────

/** 현재 필터 값으로 TODO 목록을 로드하고 렌더링한다. */
async function loadTodos() {
  const filters = {};
  if (filterCategory.value) filters.categoryId = Number(filterCategory.value);
  if (filterPriority.value) filters.priority = filterPriority.value;
  if (filterCompleted.value) filters.isCompleted = filterCompleted.value;

  const data = await withErrorHandling(
    () => fetchTodos(filters),
    "할 일 목록을 불러올 수 없습니다",
  );
  if (!data) return;

  renderTodoList(data);
}

/** TODO 배열을 받아서 목록 UI를 그린다. */
function renderTodoList(todos) {
  todoListEl.innerHTML = "";
  todoCount.textContent = todos.length;

  if (todos.length === 0) {
    todoEmptyMessage.style.display = "";
    return;
  }
  todoEmptyMessage.style.display = "none";

  for (const todo of todos) {
    todoListEl.appendChild(createTodoItem(todo));
  }
}

/** TODO 하나를 li 요소로 만든다. */
function createTodoItem(todo) {
  const li = document.createElement("li");
  li.className = `todo-item${todo.is_completed ? " completed" : ""}`;
  li.dataset.priority = todo.priority;
  li.dataset.id = todo.id;

  // 카테고리 이름 찾기
  const categoryName = todo.category_id
    ? categories.find((c) => c.id === todo.category_id)?.name ?? ""
    : "";

  // 태그 뱃지 HTML
  const tagsHtml = (todo.tags || [])
    .map((t) => `<span class="tag-badge">${escapeHtml(t.name)}</span>`)
    .join("");

  // 마감일 표시 (지났으면 강조)
  let dueDateHtml = "";
  if (todo.due_date) {
    const formatted = formatDate(todo.due_date);
    const isPast = new Date(todo.due_date) < new Date(new Date().toDateString());
    const style = isPast && !todo.is_completed ? 'style="color:var(--color-danger);font-weight:600;"' : "";
    dueDateHtml = `<span class="todo-meta-item" ${style}>📅 ${formatted}</span>`;
  }

  li.innerHTML = `
    <input type="checkbox" class="todo-checkbox" ${todo.is_completed ? "checked" : ""}>
    <div class="todo-body">
      <div class="todo-title">${escapeHtml(todo.title)}</div>
      ${todo.description ? `<div class="todo-description">${escapeHtml(todo.description)}</div>` : ""}
      <div class="todo-meta">
        <span class="priority-badge priority-${todo.priority}">${PRIORITY_LABELS[todo.priority]}</span>
        ${categoryName ? `<span class="todo-meta-item">📁 ${escapeHtml(categoryName)}</span>` : ""}
        ${dueDateHtml}
        ${tagsHtml}
      </div>
    </div>
    <div class="todo-actions">
      <button type="button" class="btn btn-icon btn-secondary btn-edit" title="수정">✏️</button>
      <button type="button" class="btn btn-icon btn-danger btn-delete" title="삭제">🗑️</button>
    </div>
  `;

  return li;
}

// ──────────────────────────────────────────────
// TODO 추가
// ──────────────────────────────────────────────

formAddTodo.addEventListener("submit", async (e) => {
  e.preventDefault();

  const title = inputTodoTitle.value.trim();
  if (!title) return;

  const data = {
    title,
    description: inputTodoDescription.value.trim(),
    priority: selectTodoPriority.value,
    categoryId: selectTodoCategory.value ? Number(selectTodoCategory.value) : null,
    dueDate: inputTodoDueDate.value || null,
    tagIds: Array.from(selectTodoTags.selectedOptions).map((o) => Number(o.value)),
  };

  const result = await withErrorHandling(
    () => createTodo(data),
    "할 일을 추가할 수 없습니다",
  );

  if (result) {
    showToast("할 일이 추가되었습니다!", "success");
    formAddTodo.reset();
    await loadTodos();
  }
});

// ──────────────────────────────────────────────
// TODO 완료 토글 / 삭제 / 수정 모달 열기 (이벤트 위임)
// ──────────────────────────────────────────────

todoListEl.addEventListener("click", async (e) => {
  const todoItem = e.target.closest(".todo-item");
  if (!todoItem) return;
  const todoId = Number(todoItem.dataset.id);

  // 완료 체크박스 토글
  if (e.target.classList.contains("todo-checkbox")) {
    const isCompleted = e.target.checked;
    const result = await withErrorHandling(
      () => updateTodo(todoId, { isCompleted }),
      "완료 상태를 변경할 수 없습니다",
    );
    if (result) {
      todoItem.classList.toggle("completed", isCompleted);
      showToast(isCompleted ? "완료 처리되었습니다" : "미완료로 변경되었습니다", "success");
    } else {
      // 실패 시 체크박스 원복
      e.target.checked = !isCompleted;
    }
    return;
  }

  // 삭제 버튼
  if (e.target.closest(".btn-delete")) {
    if (!confirm("정말 삭제할까요?")) return;
    const result = await withErrorHandling(
      () => deleteTodo(todoId),
      "할 일을 삭제할 수 없습니다",
    );
    if (result) {
      showToast("삭제되었습니다", "success");
      await loadTodos();
    }
    return;
  }

  // 수정 버튼
  if (e.target.closest(".btn-edit")) {
    openEditModal(todoId);
  }
});

// ──────────────────────────────────────────────
// 수정 모달
// ──────────────────────────────────────────────

/** TODO ID로 수정 모달을 열고 현재 값을 채운다. */
async function openEditModal(todoId) {
  // 현재 목록에서 해당 아이템의 데이터를 DOM에서 다시 가져오지 않고
  // API로 최신 데이터를 가져오는 대신, 현재 렌더링된 목록에서 추출하기엔 한계가 있으므로
  // 간단하게 전체 목록 재조회 후 해당 아이템을 찾는다.
  const todos = await withErrorHandling(fetchTodos, "데이터를 불러올 수 없습니다");
  if (!todos) return;

  const todo = todos.find((t) => t.id === todoId);
  if (!todo) {
    showToast("해당 할 일을 찾을 수 없습니다", "error");
    return;
  }

  editTodoId.value = todo.id;
  editTodoTitle.value = todo.title;
  editTodoDescription.value = todo.description || "";
  editTodoPriority.value = todo.priority;
  editTodoCategory.value = todo.category_id ?? "";
  editTodoDueDate.value = todo.due_date ? formatDate(todo.due_date) : "";

  // 태그 선택 복원
  const todoTagIds = (todo.tags || []).map((t) => String(t.id));
  for (const option of editTodoTags.options) {
    option.selected = todoTagIds.includes(option.value);
  }

  modalEditTodo.showModal();
}

/** 수정 폼 제출 */
formEditTodo.addEventListener("submit", async (e) => {
  e.preventDefault();

  const todoId = Number(editTodoId.value);
  const data = {
    title: editTodoTitle.value.trim(),
    description: editTodoDescription.value.trim(),
    priority: editTodoPriority.value,
    categoryId: editTodoCategory.value ? Number(editTodoCategory.value) : null,
    dueDate: editTodoDueDate.value || null,
    tagIds: Array.from(editTodoTags.selectedOptions).map((o) => Number(o.value)),
  };

  if (!data.title) {
    showToast("제목을 입력해주세요", "warning");
    return;
  }

  const result = await withErrorHandling(
    () => updateTodo(todoId, data),
    "할 일을 수정할 수 없습니다",
  );

  if (result) {
    showToast("수정되었습니다!", "success");
    modalEditTodo.close();
    await loadTodos();
  }
});

/** 수정 취소 */
btnCancelEdit.addEventListener("click", () => {
  modalEditTodo.close();
});

/** 모달 바깥 클릭으로 닫기 */
modalEditTodo.addEventListener("click", (e) => {
  if (e.target === modalEditTodo) {
    modalEditTodo.close();
  }
});

// ──────────────────────────────────────────────
// 필터
// ──────────────────────────────────────────────

btnApplyFilter.addEventListener("click", () => {
  loadTodos();
});

btnResetFilter.addEventListener("click", () => {
  filterCategory.value = "";
  filterPriority.value = "";
  filterCompleted.value = "";
  loadTodos();
});

// ──────────────────────────────────────────────
// 카테고리 관리
// ──────────────────────────────────────────────

formAddCategory.addEventListener("submit", async (e) => {
  e.preventDefault();

  const name = inputCategoryName.value.trim();
  if (!name) return;

  const result = await withErrorHandling(
    () => createCategory(name),
    "카테고리를 추가할 수 없습니다",
  );

  if (result) {
    showToast(`카테고리 "${name}" 추가됨!`, "success");
    inputCategoryName.value = "";
    await loadCategories();
  }
});

categoryList.addEventListener("click", async (e) => {
  const btn = e.target.closest(".btn-delete-item");
  if (!btn) return;

  const id = Number(btn.dataset.id);
  const cat = categories.find((c) => c.id === id);
  if (!confirm(`"${cat?.name}" 카테고리를 삭제할까요?`)) return;

  const result = await withErrorHandling(
    () => deleteCategory(id),
    "카테고리를 삭제할 수 없습니다",
  );

  if (result) {
    showToast("카테고리가 삭제되었습니다", "success");
    await loadCategories();
    await loadTodos(); // 카테고리 삭제 시 TODO에도 영향
  }
});

// ──────────────────────────────────────────────
// 태그 관리
// ──────────────────────────────────────────────

formAddTag.addEventListener("submit", async (e) => {
  e.preventDefault();

  const name = inputTagName.value.trim();
  if (!name) return;

  const result = await withErrorHandling(
    () => createTag(name),
    "태그를 추가할 수 없습니다",
  );

  if (result) {
    showToast(`태그 "${name}" 추가됨!`, "success");
    inputTagName.value = "";
    await loadTags();
  }
});

// ──────────────────────────────────────────────
// 앱 초기화
// ──────────────────────────────────────────────

async function init() {
  // 카테고리, 태그를 먼저 로드 (셀렉트 박스에 필요)
  await Promise.all([loadCategories(), loadTags()]);
  // 그 다음 TODO 목록 로드
  await loadTodos();
}

init();
