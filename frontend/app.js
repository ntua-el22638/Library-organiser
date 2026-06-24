const API_BASE_URL = "http://127.0.0.1:8000";

const bookForm = document.getElementById("book-form");
const searchForm = document.getElementById("search-form");
const resetButton = document.getElementById("reset-button");
const searchInput = document.getElementById("search-input");
const availabilityFilter = document.getElementById("availability-filter");
const booksList = document.getElementById("books-list");
const formMessage = document.getElementById("form-message");
const listMessage = document.getElementById("list-message");
const totalCount = document.getElementById("total-count");
const availableCount = document.getElementById("available-count");
const borrowedCount = document.getElementById("borrowed-count");

let books = [];

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

function renderBooks(items) {
  books = items;
  updateStats(items);

  if (!items.length) {
    booksList.innerHTML = `
      <div class="empty-state">
        <p>No books matched the current filters.</p>
      </div>
    `;
    return;
  }

  booksList.innerHTML = items
    .map(
      (book) => `
        <article class="book-card">
          <div class="book-card-header">
            <div>
              <h3 class="book-title">${escapeHtml(book.title)}</h3>
              <p class="book-meta">
                ${escapeHtml(book.author)}
                ${book.category ? ` | ${escapeHtml(book.category)}` : ""}
              </p>
            </div>
            <span class="badge ${book.availability}">
              ${formatAvailability(book.availability)}
            </span>
          </div>
          <p class="book-meta">
            Location: ${escapeHtml(book.location || "Not set")}
          </p>
          <div class="book-card-actions">
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
      `
    )
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

async function handleCreateBook(event) {
  event.preventDefault();
  const formData = new FormData(bookForm);
  const payload = {
    title: formData.get("title"),
    author: formData.get("author"),
    category: formData.get("category"),
    location: formData.get("location"),
    availability: formData.get("availability"),
  };

  setMessage(formMessage, "Saving...");
  try {
    await request("/books", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    bookForm.reset();
    bookForm.elements.availability.value = "available";
    setMessage(formMessage, "Book added successfully.");
    await loadBooks();
  } catch (error) {
    setMessage(formMessage, error.message, true);
  }
}

async function handleBookAction(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  const { action, id } = button.dataset;
  const book = books.find((item) => item.id === Number(id));
  if (!book) {
    return;
  }

  try {
    if (action === "toggle") {
      const path = book.availability === "available" ? `/books/${id}/borrow` : `/books/${id}/return`;
      await request(path, { method: "PATCH" });
    }

    if (action === "location") {
      const nextLocation = window.prompt("New book location:", book.location || "");
      if (!nextLocation) {
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
    }

    await loadBooks();
  } catch (error) {
    setMessage(listMessage, error.message, true);
  }
}

function handleResetFilters() {
  searchForm.reset();
  loadBooks();
}

bookForm.addEventListener("submit", handleCreateBook);
searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadBooks();
});
resetButton.addEventListener("click", handleResetFilters);
booksList.addEventListener("click", handleBookAction);

loadBooks();
