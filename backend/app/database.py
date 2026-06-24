from __future__ import annotations

import re
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
                    shelf_column INTEGER NOT NULL DEFAULT 1,
                    shelf_row INTEGER NOT NULL DEFAULT 1,
                    availability TEXT NOT NULL CHECK (availability IN ('available', 'borrowed')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._ensure_column(connection, "shelf_column", "INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(connection, "shelf_row", "INTEGER NOT NULL DEFAULT 1")
            self._backfill_shelf_positions(connection)
            connection.commit()

    def _ensure_column(self, connection: sqlite3.Connection, column_name: str, definition: str) -> None:
        existing_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(books)").fetchall()
        }
        if column_name not in existing_columns:
            connection.execute(f"ALTER TABLE books ADD COLUMN {column_name} {definition}")

    def _backfill_shelf_positions(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            "SELECT id, location, shelf_column, shelf_row FROM books"
        ).fetchall()

        for row in rows:
            shelf_column = row["shelf_column"] or 1
            shelf_row = row["shelf_row"] or 1
            parsed_column, parsed_row = self._parse_legacy_location(row["location"])

            if parsed_column is not None:
                shelf_column = parsed_column
            if parsed_row is not None:
                shelf_row = parsed_row

            connection.execute(
                """
                UPDATE books
                SET shelf_column = ?, shelf_row = ?, location = ?
                WHERE id = ?
                """,
                (shelf_column, shelf_row, self._format_location(shelf_column, shelf_row), row["id"]),
            )

    def _parse_legacy_location(self, value: str) -> tuple[int | None, int | None]:
        if not value:
            return None, None

        match = re.search(r"([A-Za-z])\s*[-/ ]\s*(\d+)", value)
        if match:
            column = ord(match.group(1).upper()) - 64
            row = int(match.group(2))
            return column, row

        number_match = re.findall(r"\d+", value)
        if len(number_match) >= 2:
            return int(number_match[0]), int(number_match[1])
        if len(number_match) == 1:
            return None, int(number_match[0])

        return None, None

    def _format_location(self, shelf_column: int, shelf_row: int) -> str:
        return f"Column {shelf_column} / Row {shelf_row}"

    def create_book(self, payload: dict[str, Any]) -> sqlite3.Row:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO books (title, author, category, location, shelf_column, shelf_row, availability)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["title"],
                    payload["author"],
                    payload["category"],
                    self._format_location(payload["shelf_column"], payload["shelf_row"]),
                    payload["shelf_column"],
                    payload["shelf_row"],
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

        statement += " ORDER BY shelf_row ASC, shelf_column ASC, updated_at DESC, id DESC"

        with self._connect() as connection:
            return connection.execute(statement, parameters).fetchall()

    def update_book(self, book_id: int, payload: dict[str, Any]) -> sqlite3.Row | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE books
                SET title = ?, author = ?, category = ?, location = ?, shelf_column = ?, shelf_row = ?,
                    availability = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    payload["title"],
                    payload["author"],
                    payload["category"],
                    self._format_location(payload["shelf_column"], payload["shelf_row"]),
                    payload["shelf_column"],
                    payload["shelf_row"],
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

    def update_location(self, book_id: int, shelf_column: int, shelf_row: int) -> sqlite3.Row | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE books
                SET location = ?, shelf_column = ?, shelf_row = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (self._format_location(shelf_column, shelf_row), shelf_column, shelf_row, book_id),
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
