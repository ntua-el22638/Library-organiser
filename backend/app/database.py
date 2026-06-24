from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .schemas import Availability


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        if self.db_path.parent != Path("."):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    location TEXT NOT NULL DEFAULT '',
                    availability TEXT NOT NULL CHECK (availability IN ('available', 'borrowed')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()

    def create_book(self, payload: dict[str, Any]) -> sqlite3.Row:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO books (title, author, category, location, availability)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload["title"],
                    payload["author"],
                    payload["category"],
                    payload["location"],
                    payload["availability"],
                ),
            )
            connection.commit()
            return self.get_book(cursor.lastrowid, connection)

    def get_book(self, book_id: int, connection: sqlite3.Connection | None = None) -> sqlite3.Row | None:
        owns_connection = connection is None
        connection = connection or self._connect()
        try:
            return connection.execute(
                "SELECT * FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
        finally:
            if owns_connection:
                connection.close()

    def list_books(self, query: str = "", availability: str | None = None) -> list[sqlite3.Row]:
        statement = "SELECT * FROM books"
        conditions = []
        parameters: list[Any] = []

        if query:
            like_query = f"%{query}%"
            conditions.append(
                "(title LIKE ? OR author LIKE ? OR category LIKE ?)"
            )
            parameters.extend([like_query, like_query, like_query])

        if availability:
            conditions.append("availability = ?")
            parameters.append(availability)

        if conditions:
            statement += " WHERE " + " AND ".join(conditions)

        statement += " ORDER BY updated_at DESC, id DESC"

        with self._connect() as connection:
            return connection.execute(statement, parameters).fetchall()

    def update_book(self, book_id: int, payload: dict[str, Any]) -> sqlite3.Row | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE books
                SET title = ?, author = ?, category = ?, location = ?, availability = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    payload["title"],
                    payload["author"],
                    payload["category"],
                    payload["location"],
                    payload["availability"],
                    book_id,
                ),
            )
            connection.commit()
            if cursor.rowcount == 0:
                return None
            return self.get_book(book_id, connection)

    def update_availability(self, book_id: int, availability: Availability) -> sqlite3.Row | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE books
                SET availability = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (availability.value, book_id),
            )
            connection.commit()
            if cursor.rowcount == 0:
                return None
            return self.get_book(book_id, connection)

    def update_location(self, book_id: int, location: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE books
                SET location = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (location, book_id),
            )
            connection.commit()
            if cursor.rowcount == 0:
                return None
            return self.get_book(book_id, connection)

    def delete_book(self, book_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM books WHERE id = ?",
                (book_id,),
            )
            connection.commit()
            return cursor.rowcount > 0
