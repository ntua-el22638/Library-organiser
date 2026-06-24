from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_SHELF_COLUMNS = 4
MAX_SHELF_ROWS = 6


class Availability(str, Enum):
    AVAILABLE = "available"
    BORROWED = "borrowed"


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    category: str = Field(default="", max_length=255)
    shelf_column: int = Field(default=1, ge=1, le=MAX_SHELF_COLUMNS)
    shelf_row: int = Field(default=1, ge=1, le=MAX_SHELF_ROWS)
    availability: Availability = Availability.AVAILABLE

    @field_validator("title", "author", "category", mode="before")
    @classmethod
    def strip_strings(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def validate_location(self) -> "BookBase":
        if self.availability == Availability.AVAILABLE and (not self.shelf_column or not self.shelf_row):
            raise ValueError("Shelf column and row are required when the book is available.")
        return self


class BookCreate(BookBase):
    pass


class BookUpdate(BookBase):
    pass


class LocationUpdate(BaseModel):
    shelf_column: int = Field(..., ge=1, le=MAX_SHELF_COLUMNS)
    shelf_row: int = Field(..., ge=1, le=MAX_SHELF_ROWS)


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    category: str
    shelf_column: int
    shelf_row: int
    availability: Availability
    created_at: datetime
    updated_at: datetime


class BookListResponse(BaseModel):
    items: list[BookResponse]
    total: int
