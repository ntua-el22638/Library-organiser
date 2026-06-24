# Library Organiser

Μικρή web εφαρμογή για οργάνωση προσωπικής βιβλιοθήκης με:
- `backend/` σε Python + FastAPI
- `frontend/` σε HTML + CSS + JavaScript
- SQLite βάση για τα βιβλία και τη διαθεσιμότητά τους

## Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Το API τρέχει στο `http://127.0.0.1:8000`.

## Frontend

Άνοιξε το [frontend/index.html](./frontend/index.html) σε browser ή σέρβιρέ το με ένα απλό static server.

Το frontend περιμένει το API στο `http://127.0.0.1:8000`.

## Βασικά endpoints

- `POST /books`
- `GET /books`
- `GET /books/search?q=...`
- `GET /books/{id}`
- `PUT /books/{id}`
- `PATCH /books/{id}/borrow`
- `PATCH /books/{id}/return`
- `PATCH /books/{id}/location` (updates `shelf_column` and `shelf_row`)
- `DELETE /books/{id}`
