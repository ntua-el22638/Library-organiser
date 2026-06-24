from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def create_client(tmp_path: Path) -> TestClient:
    app = create_app(str(tmp_path / "test-library.db"))
    return TestClient(app)


def test_create_book_success(tmp_path: Path) -> None:
    client = create_client(tmp_path)

    response = client.post(
        "/books",
        json={
            "title": "The Hobbit",
            "author": "J.R.R. Tolkien",
            "category": "Fantasy",
            "location": "Shelf A-1",
            "availability": "available",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "The Hobbit"
    assert data["availability"] == "available"


def test_create_book_requires_author(tmp_path: Path) -> None:
    client = create_client(tmp_path)

    response = client.post(
        "/books",
        json={
            "title": "The Hobbit",
            "author": "",
            "category": "Fantasy",
            "location": "Shelf A-1",
            "availability": "available",
        },
    )

    assert response.status_code == 422


def test_search_finds_available_and_borrowed_books(tmp_path: Path) -> None:
    client = create_client(tmp_path)

    first = client.post(
        "/books",
        json={
            "title": "Dune",
            "author": "Frank Herbert",
            "category": "Sci-Fi",
            "location": "Shelf B-2",
            "availability": "available",
        },
    ).json()
    second = client.post(
        "/books",
        json={
            "title": "Dune Messiah",
            "author": "Frank Herbert",
            "category": "Sci-Fi",
            "location": "Shelf B-3",
            "availability": "available",
        },
    ).json()

    client.patch(f"/books/{second['id']}/borrow")

    available_response = client.get("/books/search", params={"q": "Dune", "availability": "available"})
    borrowed_response = client.get("/books/search", params={"q": "Dune", "availability": "borrowed"})

    assert available_response.status_code == 200
    assert borrowed_response.status_code == 200
    assert available_response.json()["items"][0]["id"] == first["id"]
    assert borrowed_response.json()["items"][0]["id"] == second["id"]


def test_borrow_and_return_flow(tmp_path: Path) -> None:
    client = create_client(tmp_path)
    created = client.post(
        "/books",
        json={
            "title": "Neuromancer",
            "author": "William Gibson",
            "category": "Cyberpunk",
            "location": "Shelf C-4",
            "availability": "available",
        },
    ).json()

    borrow_response = client.patch(f"/books/{created['id']}/borrow")
    return_response = client.patch(f"/books/{created['id']}/return")

    assert borrow_response.status_code == 200
    assert borrow_response.json()["availability"] == "borrowed"
    assert return_response.status_code == 200
    assert return_response.json()["availability"] == "available"


def test_change_location(tmp_path: Path) -> None:
    client = create_client(tmp_path)
    created = client.post(
        "/books",
        json={
            "title": "Foundation",
            "author": "Isaac Asimov",
            "category": "Sci-Fi",
            "location": "Shelf D-1",
            "availability": "available",
        },
    ).json()

    response = client.patch(
        f"/books/{created['id']}/location",
        json={"location": "Shelf D-5"},
    )

    assert response.status_code == 200
    assert response.json()["location"] == "Shelf D-5"


def test_delete_book_removes_it_from_results(tmp_path: Path) -> None:
    client = create_client(tmp_path)
    created = client.post(
        "/books",
        json={
            "title": "Snow Crash",
            "author": "Neal Stephenson",
            "category": "Sci-Fi",
            "location": "Shelf E-1",
            "availability": "available",
        },
    ).json()

    delete_response = client.delete(f"/books/{created['id']}")
    list_response = client.get("/books", params={"q": "Snow"})

    assert delete_response.status_code == 204
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 0
