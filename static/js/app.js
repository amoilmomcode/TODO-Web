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
  deleteTag,
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

// TODO 목록
const todoListEl = $("#todo-list");
const todoCount = $("#todo-count");
const todoEmptyMessage = $("#todo-empty-message");
const btnOpenAddModal = $("#btn-open-add-modal");

// 뷰 토글
const btnViewList = $("#btn-view-list");
const btnViewCalendar = $("#btn-view-calendar");
const viewList = $("#view-list");
const viewCalendar = $("#view-calendar");

// 달력
const calendarMonthLabel = $("#calendar-month-label");
const calendarDays = $("#calendar-days");
const btnPrevMonth = $("#btn-prev-month");
const btnNextMonth = $("#btn-next-month");
const btnCalendarToday = $("#btn-calendar-today");

// 통합 모달 (추가/수정)
const modalTodo = $("#modal-todo");
const formTodoModal = $("#form-todo-modal");
const modalTodoTitle = $("#modal-todo-title");
const modalTodoId = $("#modal-todo-id");
const modalTodoInputTitle = $("#modal-todo-input-title");
const modalTodoDescription = $("#modal-todo-description");
const modalTodoPriority = $("#modal-todo-priority");
const modalTodoCategory = $("#modal-todo-category");
const modalTodoDueDate = $("#modal-todo-due-date");
const modalTodoTags = $("#modal-todo-tags");
const modalTodoSubmitBtn = $("#modal-todo-submit-btn");
const btnCancelModal = $("#btn-cancel-modal");

// ──────────────────────────────────────────────
// 상태
// ──────────────────────────────────────────────

let categories = [];
let tags = [];
let currentViewMode = localStorage.getItem("viewMode") || "list";
let calendarYear = new Date().getFullYear();
let calendarMonth = new Date().getMonth(); // 0-indexed
let cachedTodos = []; // 달력 렌더링용 캐시

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
  const selects = [filterCategory, modalTodoCategory];
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
  const selects = [modalTodoTags];
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
      <button type="button" class="btn-delete-item" data-id="${tag.id}" title="삭제">✕</button>
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

  cachedTodos = data;
  renderTodoList(data);
  renderCalendar();
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
// 통합 모달 (추가/수정)
// ──────────────────────────────────────────────

/** 모달을 추가 모드로 연다. */
function openAddModal() {
  modalTodoId.value = "";
  formTodoModal.reset();
  modalTodoTitle.textContent = "새 할 일 추가";
  modalTodoSubmitBtn.textContent = "추가";
  modalTodo.showModal();
  modalTodoInputTitle.focus();
}

/** 모달을 수정 모드로 열고, 기존 데이터를 채운다. */
async function openEditModal(todoId) {
  const todos = await withErrorHandling(fetchTodos, "데이터를 불러올 수 없습니다");
  if (!todos) return;

  const todo = todos.find((t) => t.id === todoId);
  if (!todo) {
    showToast("해당 할 일을 찾을 수 없습니다", "error");
    return;
  }

  modalTodoId.value = todo.id;
  modalTodoInputTitle.value = todo.title;
  modalTodoDescription.value = todo.description || "";
  modalTodoPriority.value = todo.priority;
  modalTodoCategory.value = todo.category_id ?? "";
  modalTodoDueDate.value = todo.due_date ? formatDate(todo.due_date) : "";

  // 태그 선택 복원
  const todoTagIds = (todo.tags || []).map((t) => String(t.id));
  for (const option of modalTodoTags.options) {
    option.selected = todoTagIds.includes(option.value);
  }

  modalTodoTitle.textContent = "할 일 수정";
  modalTodoSubmitBtn.textContent = "저장";
  modalTodo.showModal();
  modalTodoInputTitle.focus();
}

/** 모달 닫기 */
function closeModal() {
  modalTodo.close();
}

/** 추가 버튼 클릭 */
btnOpenAddModal.addEventListener("click", openAddModal);

/** 모달 폼 제출 (추가/수정 분기) */
formTodoModal.addEventListener("submit", async (e) => {
  e.preventDefault();

  const title = modalTodoInputTitle.value.trim();
  if (!title) {
    showToast("제목을 입력해주세요", "warning");
    return;
  }

  const data = {
    title,
    description: modalTodoDescription.value.trim(),
    priority: modalTodoPriority.value,
    categoryId: modalTodoCategory.value ? Number(modalTodoCategory.value) : null,
    dueDate: modalTodoDueDate.value || null,
    tagIds: Array.from(modalTodoTags.selectedOptions).map((o) => Number(o.value)),
  };

  const isEditMode = !!modalTodoId.value;

  if (isEditMode) {
    // 수정 모드
    const todoId = Number(modalTodoId.value);
    const result = await withErrorHandling(
      () => updateTodo(todoId, data),
      "할 일을 수정할 수 없습니다",
    );
    if (result) {
      showToast("수정되었습니다!", "success");
      closeModal();
      await loadTodos();
    }
  } else {
    // 추가 모드
    const result = await withErrorHandling(
      () => createTodo(data),
      "할 일을 추가할 수 없습니다",
    );
    if (result) {
      showToast("할 일이 추가되었습니다!", "success");
      closeModal();
      await loadTodos();
    }
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
// 모달 닫기 이벤트
// ──────────────────────────────────────────────

/** 취소 버튼 클릭 */
btnCancelModal.addEventListener("click", closeModal);

/** 오버레이(backdrop) 클릭으로 닫기 */
modalTodo.addEventListener("click", (e) => {
  if (e.target === modalTodo) {
    closeModal();
  }
});

/** ESC 키로 닫기 (dialog 기본 동작이지만 명시적으로 처리) */
modalTodo.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeModal();
  }
});

// ──────────────────────────────────────────────
// 뷰 토글 (리스트 ↔ 달력)
// ──────────────────────────────────────────────

/** 뷰 모드를 전환한다. */
function switchView(mode) {
  currentViewMode = mode;
  localStorage.setItem("viewMode", mode);

  btnViewList.classList.toggle("active", mode === "list");
  btnViewCalendar.classList.toggle("active", mode === "calendar");

  viewList.style.display = mode === "list" ? "" : "none";
  viewCalendar.style.display = mode === "calendar" ? "" : "none";

  if (mode === "calendar") {
    renderCalendar();
  }
}

btnViewList.addEventListener("click", () => switchView("list"));
btnViewCalendar.addEventListener("click", () => switchView("calendar"));

// ──────────────────────────────────────────────
// 달력 렌더링
// ──────────────────────────────────────────────

/** 월 라벨을 업데이트한다. */
function updateMonthLabel() {
  calendarMonthLabel.textContent = `${calendarYear}년 ${calendarMonth + 1}월`;
}

/** 달력 그리드를 렌더링한다. */
function renderCalendar() {
  updateMonthLabel();
  calendarDays.innerHTML = "";

  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

  // 해당 월의 첫째 날과 마지막 날
  const firstDay = new Date(calendarYear, calendarMonth, 1);
  const lastDay = new Date(calendarYear, calendarMonth + 1, 0);

  // 시작 요일 (0=일 ~ 6=토)
  const startDow = firstDay.getDay();
  const totalDays = lastDay.getDate();

  // 이전 달 마지막 날
  const prevLastDay = new Date(calendarYear, calendarMonth, 0).getDate();

  // TODO를 날짜별로 그룹핑
  const todosByDate = {};
  for (const todo of cachedTodos) {
    if (!todo.due_date) continue;
    const dateKey = formatDate(todo.due_date);
    if (!todosByDate[dateKey]) todosByDate[dateKey] = [];
    todosByDate[dateKey].push(todo);
  }

  // 이전 달 날짜 채우기
  for (let i = startDow - 1; i >= 0; i--) {
    const day = prevLastDay - i;
    const prevMonth = calendarMonth - 1;
    const prevYear = prevMonth < 0 ? calendarYear - 1 : calendarYear;
    const actualMonth = prevMonth < 0 ? 12 : prevMonth + 1;
    const dateStr = `${prevYear}-${String(actualMonth).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const todos = todosByDate[dateStr] || [];
    const dow = new Date(prevYear, actualMonth - 1, day).getDay();
    calendarDays.appendChild(createDayCell(day, dateStr, true, todayStr, dow, todos));
  }

  // 이번 달 날짜 채우기
  for (let day = 1; day <= totalDays; day++) {
    const dateStr = `${calendarYear}-${String(calendarMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const dow = (startDow + day - 1) % 7;
    const todos = todosByDate[dateStr] || [];
    calendarDays.appendChild(createDayCell(day, dateStr, false, todayStr, dow, todos));
  }

  // 다음 달 날짜 채우기 (6주 맞추기)
  const cellsSoFar = startDow + totalDays;
  const totalCells = cellsSoFar <= 35 ? 35 : 42;
  const remaining = totalCells - cellsSoFar;
  for (let day = 1; day <= remaining; day++) {
    const nextMonth = calendarMonth + 1;
    const nextYear = nextMonth > 11 ? calendarYear + 1 : calendarYear;
    const actualMonth = nextMonth > 11 ? 1 : nextMonth + 1;
    const dateStr = `${nextYear}-${String(actualMonth).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const todos = todosByDate[dateStr] || [];
    const dow = new Date(nextYear, actualMonth - 1, day).getDay();
    calendarDays.appendChild(createDayCell(day, dateStr, true, todayStr, dow, todos));
  }

}

/** 날짜 셀 하나를 생성한다. */
function createDayCell(day, dateStr, isOtherMonth, todayStr, dow, todos = []) {
  const cell = document.createElement("div");
  cell.className = "calendar-day";
  cell.dataset.date = dateStr;

  if (isOtherMonth) cell.classList.add("other-month");
  if (dateStr === todayStr) cell.classList.add("today");
  if (dow === 0) cell.classList.add("sunday");
  if (dow === 6) cell.classList.add("saturday");

  // 날짜 숫자
  const numberEl = document.createElement("div");
  numberEl.className = "calendar-day-number";
  numberEl.textContent = day;
  cell.appendChild(numberEl);

  // TODO 목록
  if (todos.length > 0) {
    const listEl = document.createElement("div");
    listEl.className = "calendar-todo-list";

    const maxShow = 3;
    const showTodos = todos.slice(0, maxShow);

    for (const todo of showTodos) {
      const item = document.createElement("div");
      item.className = `calendar-todo-item priority-${todo.priority}`;
      if (todo.is_completed) item.classList.add("completed");
      item.textContent = todo.title;
      item.title = todo.title; // 툴팁
      item.dataset.todoId = todo.id;

      // TODO 클릭 → 수정 모달
      item.addEventListener("click", (e) => {
        e.stopPropagation();
        openEditModal(Number(todo.id));
      });

      listEl.appendChild(item);
    }

    // 더보기 표시
    if (todos.length > maxShow) {
      const more = document.createElement("div");
      more.className = "calendar-todo-more";
      more.textContent = `+${todos.length - maxShow}개 더`;
      listEl.appendChild(more);
    }

    cell.appendChild(listEl);
  }

  // 날짜 클릭 → 추가 모달 (마감일 자동 세팅)
  cell.addEventListener("click", () => {
    openAddModalWithDate(dateStr);
  });

  return cell;
}

/** 마감일이 세팅된 추가 모달을 연다. */
function openAddModalWithDate(dateStr) {
  modalTodoId.value = "";
  formTodoModal.reset();
  modalTodoTitle.textContent = "새 할 일 추가";
  modalTodoSubmitBtn.textContent = "추가";
  modalTodoDueDate.value = dateStr;
  modalTodo.showModal();
  modalTodoInputTitle.focus();
}

// 달력 네비게이션
btnPrevMonth.addEventListener("click", () => {
  calendarMonth--;
  if (calendarMonth < 0) {
    calendarMonth = 11;
    calendarYear--;
  }
  renderCalendar();
});

btnNextMonth.addEventListener("click", () => {
  calendarMonth++;
  if (calendarMonth > 11) {
    calendarMonth = 0;
    calendarYear++;
  }
  renderCalendar();
});

btnCalendarToday.addEventListener("click", () => {
  const now = new Date();
  calendarYear = now.getFullYear();
  calendarMonth = now.getMonth();
  renderCalendar();
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

tagList.addEventListener("click", async (e) => {
  const btn = e.target.closest(".btn-delete-item");
  if (!btn) return;

  const id = Number(btn.dataset.id);
  const tag = tags.find((t) => t.id === id);
  if (!confirm(`"${tag?.name}" 태그를 삭제할까요?`)) return;

  const result = await withErrorHandling(
    () => deleteTag(id),
    "태그를 삭제할 수 없습니다",
  );

  if (result) {
    showToast("태그가 삭제되었습니다", "success");
    await loadTags();
    await loadTodos(); // 태그 정보 갱신
  }
});

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
  // 저장된 뷰 모드 복원
  switchView(currentViewMode);

  // 카테고리, 태그를 먼저 로드 (셀렉트 박스에 필요)
  await Promise.all([loadCategories(), loadTags()]);
  // 그 다음 TODO 목록 로드
  await loadTodos();
}

init();
