from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class Availability(str, Enum):
    AVAILABLE = "available"
    BORROWED = "borrowed"


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    category: str = Field(default="", max_length=255)
    location: str = Field(default="", max_length=255)
    availability: Availability = Availability.AVAILABLE

    @field_validator("title", "author", "category", "location", mode="before")
    @classmethod
    def strip_strings(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def validate_location(self) -> "BookBase":
        if self.availability == Availability.AVAILABLE and not self.location:
            raise ValueError("Location is required when the book is available.")
        return self


class BookCreate(BookBase):
    pass


class BookUpdate(BookBase):
    pass


class LocationUpdate(BaseModel):
    location: str = Field(..., min_length=1, max_length=255)

    @field_validator("location", mode="before")
    @classmethod
    def strip_location(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    category: str
    location: str
    availability: Availability
    created_at: datetime
    updated_at: datetime


class BookListResponse(BaseModel):
    items: list[BookResponse]
    total: int
