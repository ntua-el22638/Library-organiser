const API_BASE_URL = "http://127.0.0.1:8000";

const bookForm = document.getElementById("book-form");
const categoryInputs = document.querySelectorAll('input[name="category"]');
const formTitle = document.getElementById("form-title");
const formDescription = document.getElementById("form-description");
const submitButton = document.getElementById("submit-button");
const cancelEditButton = document.getElementById("cancel-edit-button");
const searchForm = document.getElementById("search-form");
const resetButton = document.getElementById("reset-button");
const searchInput = document.getElementById("search-input");
const availabilityFilter = document.getElementById("availability-filter");
const booksList = document.getElementById("books-list");
const bulkActions = document.getElementById("bulk-actions");
const selectionCount = document.getElementById("selection-count");
const deleteSelectedButton = document.getElementById("delete-selected-button");
const clearSelectionButton = document.getElementById("clear-selection-button");
const formMessage = document.getElementById("form-message");
const listMessage = document.getElementById("list-message");
const totalCount = document.getElementById("total-count");
const availableCount = document.getElementById("available-count");
const borrowedCount = document.getElementById("borrowed-count");

let books = [];
let editingBookId = null;
let selectedBookIds = new Set();
const CATEGORY_SEPARATOR = ", ";

function setMessage(element, message = "", isError = false) {
  element.textContent = message;
  element.classList.toggle("error", isError);
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join(", ")
      : data.detail;
    throw new Error(detail || "Request failed.");
  }

  return data;
}

function formatAvailability(value) {
  return value === "available" ? "Available in library" : "Borrowed";
}

function updateStats(items) {
  totalCount.textContent = items.length;
  availableCount.textContent = items.filter((item) => item.availability === "available").length;
  borrowedCount.textContent = items.filter((item) => item.availability === "borrowed").length;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function updateBulkActions() {
  const count = selectedBookIds.size;
  selectionCount.textContent = `${count} selected`;
  bulkActions.classList.toggle("hidden", count === 0);
}

function resetFormState() {
  editingBookId = null;
  bookForm.reset();
  bookForm.elements.availability.value = "available";
  cancelEditButton.classList.add("hidden");
}

function setCreateMode() {
  resetFormState();
  formTitle.textContent = "Add book";
  formDescription.textContent = "Create a new record in your library.";
  submitButton.textContent = "Save book";
  setMessage(formMessage, "");
}

function setSelectedCategories(value = "") {
  const selectedCategories = new Set(
    String(value)
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
  );

  Array.from(categoryInputs).forEach((input) => {
    input.checked = selectedCategories.has(input.value);
  });
}

function setEditMode(book) {
  editingBookId = book.id;
  bookForm.elements.title.value = book.title;
  bookForm.elements.author.value = book.author;
  setSelectedCategories(book.category || "");
  bookForm.elements.location.value = book.location || "";
  bookForm.elements.availability.value = book.availability;
  formTitle.textContent = "Edit book";
  formDescription.textContent = `Editing "${book.title}".`;
  submitButton.textContent = "Update book";
  cancelEditButton.classList.remove("hidden");
  setMessage(formMessage, `Editing "${book.title}".`);
  bookForm.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderBooks(items) {
  books = items;
  selectedBookIds = new Set([...selectedBookIds].filter((id) => items.some((item) => item.id === id)));
  updateStats(items);
  updateBulkActions();

  if (!items.length) {
    booksList.innerHTML = `
      <div class="empty-state">
        <p>No books matched the current filters.</p>
      </div>
    `;
    return;
  }

  booksList.innerHTML = items
    .map((book) => {
      const isSelected = selectedBookIds.has(book.id);

      return `
        <article class="book-card ${isSelected ? "selected" : ""}">
          <div class="book-card-header">
            <label class="select-book">
              <input type="checkbox" data-action="select" data-id="${book.id}" ${isSelected ? "checked" : ""} />
              <span>Select</span>
            </label>
            <span class="badge ${book.availability}">
              ${formatAvailability(book.availability)}
            </span>
          </div>
          <div>
            <h3 class="book-title">${escapeHtml(book.title)}</h3>
            <p class="book-meta">
              ${escapeHtml(book.author)}
              ${book.category ? ` | ${escapeHtml(book.category)}` : ""}
            </p>
          </div>
          <p class="book-meta">
            Location: ${escapeHtml(book.location || "Not set")}
          </p>
          <div class="book-card-actions">
            <button type="button" class="ghost-button" data-action="edit" data-id="${book.id}">
              Edit
            </button>
            <button type="button" data-action="toggle" data-id="${book.id}">
              ${book.availability === "available" ? "Mark as borrowed" : "Return to library"}
            </button>
            <button type="button" class="ghost-button" data-action="location" data-id="${book.id}">
              Change location
            </button>
            <button type="button" class="ghost-button" data-action="delete" data-id="${book.id}">
              Delete
            </button>
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadBooks() {
  const query = searchInput.value.trim();
  const availability = availabilityFilter.value;
  const params = new URLSearchParams();

  if (query) {
    params.set("q", query);
  }
  if (availability) {
    params.set("availability", availability);
  }

  const path = query ? `/books/search?${params.toString()}` : `/books?${params.toString()}`;

  setMessage(listMessage, "Loading books...");
  try {
    const data = await request(path);
    renderBooks(data.items);
    setMessage(listMessage, `${data.total} books shown.`);
  } catch (error) {
    renderBooks([]);
    setMessage(listMessage, error.message, true);
  }
}

function buildBookPayload() {
  const formData = new FormData(bookForm);

  return {
    title: formData.get("title"),
    author: formData.get("author"),
    category: Array.from(categoryInputs)
      .filter((input) => input.checked)
      .map((input) => input.value)
      .join(CATEGORY_SEPARATOR),
    location: formData.get("location"),
    availability: formData.get("availability"),
  };
}

async function handleSaveBook(event) {
  event.preventDefault();
  const payload = buildBookPayload();
  const isEditing = editingBookId !== null;
  const successMessage = isEditing ? "Book updated successfully." : "Book added successfully.";

  setMessage(formMessage, isEditing ? "Updating..." : "Saving...");
  try {
    if (isEditing) {
      await request(`/books/${editingBookId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
    } else {
      await request("/books", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    }

    setCreateMode();
    setMessage(formMessage, successMessage);
    await loadBooks();
  } catch (error) {
    setMessage(formMessage, error.message, true);
  }
}

function toggleSelection(bookId, checked) {
  if (checked) {
    selectedBookIds.add(bookId);
  } else {
    selectedBookIds.delete(bookId);
  }
  updateBulkActions();
}

async function handleBookAction(event) {
  const target = event.target;
  const checkbox = target.closest('input[type="checkbox"][data-action="select"]');
  if (checkbox) {
    toggleSelection(Number(checkbox.dataset.id), checkbox.checked);
    checkbox.closest(".book-card")?.classList.toggle("selected", checkbox.checked);
    return;
  }

  const button = target.closest("button[data-action]");
  if (!button) {
    return;
  }

  const { action, id } = button.dataset;
  const book = books.find((item) => item.id === Number(id));
  if (!book) {
    return;
  }

  try {
    if (action === "edit") {
      setEditMode(book);
      return;
    }

    if (action === "toggle") {
      const path = book.availability === "available" ? `/books/${id}/borrow` : `/books/${id}/return`;
      await request(path, { method: "PATCH" });
    }

    if (action === "location") {
      const nextLocation = window.prompt("New book location:", book.location || "");
      if (nextLocation === null) {
        return;
      }
      await request(`/books/${id}/location`, {
        method: "PATCH",
        body: JSON.stringify({ location: nextLocation }),
      });
    }

    if (action === "delete") {
      const confirmed = window.confirm(`Delete "${book.title}" from the database?`);
      if (!confirmed) {
        return;
      }
      await request(`/books/${id}`, { method: "DELETE" });
      selectedBookIds.delete(book.id);
      if (editingBookId === book.id) {
        setCreateMode();
      }
    }

    await loadBooks();
  } catch (error) {
    setMessage(listMessage, error.message, true);
  }
}

async function handleDeleteSelected() {
  const selectedBooks = books.filter((book) => selectedBookIds.has(book.id));
  if (!selectedBooks.length) {
    return;
  }

  const confirmed = window.confirm(`Delete ${selectedBooks.length} selected book(s)?`);
  if (!confirmed) {
    return;
  }

  setMessage(listMessage, "Deleting selected books...");
  try {
    await Promise.all(selectedBooks.map((book) => request(`/books/${book.id}`, { method: "DELETE" })));
    if (editingBookId !== null && selectedBookIds.has(editingBookId)) {
      setCreateMode();
    }
    selectedBookIds.clear();
    await loadBooks();
    setMessage(listMessage, `${selectedBooks.length} books deleted.`);
  } catch (error) {
    setMessage(listMessage, error.message, true);
  }
}

function handleResetFilters() {
  searchForm.reset();
  loadBooks();
}

bookForm.addEventListener("submit", handleSaveBook);
cancelEditButton.addEventListener("click", setCreateMode);
searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadBooks();
});
resetButton.addEventListener("click", handleResetFilters);
deleteSelectedButton.addEventListener("click", handleDeleteSelected);
clearSelectionButton.addEventListener("click", () => {
  selectedBookIds.clear();
  renderBooks(books);
});
booksList.addEventListener("click", handleBookAction);
booksList.addEventListener("change", handleBookAction);

setCreateMode();
loadBooks();
