from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .database import Database
from .schemas import (
    Availability,
    BookCreate,
    BookListResponse,
    BookResponse,
    BookUpdate,
    LocationUpdate,
)


def build_book_response(row) -> BookResponse:
    return BookResponse.model_validate(dict(row))


def create_app(db_path: str | None = None) -> FastAPI:
    database = Database(db_path or os.getenv("LIBRARY_DB_PATH", "backend/library.db"))
    database.init()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield

    app = FastAPI(
        title="Library Organiser API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/books", response_model=BookResponse, status_code=201)
    def create_book(payload: BookCreate) -> BookResponse:
        row = database.create_book(payload.model_dump())
        return build_book_response(row)

    @app.get("/books/search", response_model=BookListResponse)
    def search_books(
        q: str = Query(..., min_length=1),
        availability: Availability | None = None,
    ) -> BookListResponse:
        rows = database.list_books(query=q.strip(), availability=availability.value if availability else None)
        items = [build_book_response(row) for row in rows]
        return BookListResponse(items=items, total=len(items))

    @app.get("/books", response_model=BookListResponse)
    def list_books(
        q: str = Query(default=""),
        availability: Availability | None = None,
    ) -> BookListResponse:
        rows = database.list_books(query=q.strip(), availability=availability.value if availability else None)
        items = [build_book_response(row) for row in rows]
        return BookListResponse(items=items, total=len(items))

    @app.get("/books/{book_id}", response_model=BookResponse)
    def get_book(book_id: int) -> BookResponse:
        row = database.get_book(book_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Book not found.")
        return build_book_response(row)

    @app.put("/books/{book_id}", response_model=BookResponse)
    def update_book(book_id: int, payload: BookUpdate) -> BookResponse:
        row = database.update_book(book_id, payload.model_dump())
        if row is None:
            raise HTTPException(status_code=404, detail="Book not found.")
        return build_book_response(row)

    @app.patch("/books/{book_id}/borrow", response_model=BookResponse)
    def borrow_book(book_id: int) -> BookResponse:
        existing = database.get_book(book_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Book not found.")
        row = database.update_availability(book_id, Availability.BORROWED)
        return build_book_response(row)

    @app.patch("/books/{book_id}/return", response_model=BookResponse)
    def return_book(book_id: int) -> BookResponse:
        existing = database.get_book(book_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Book not found.")
        if not existing["shelf_column"] or not existing["shelf_row"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot return a book without a shelf position.",
            )
        row = database.update_availability(book_id, Availability.AVAILABLE)
        return build_book_response(row)

    @app.patch("/books/{book_id}/location", response_model=BookResponse)
    def update_location(book_id: int, payload: LocationUpdate) -> BookResponse:
        existing = database.get_book(book_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Book not found.")
        row = database.update_location(book_id, payload.shelf_column, payload.shelf_row)
        return build_book_response(row)

    @app.delete("/books/{book_id}", status_code=204)
    def delete_book(book_id: int) -> Response:
        deleted = database.delete_book(book_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Book not found.")
        return Response(status_code=204)

    return app


app = create_app()
