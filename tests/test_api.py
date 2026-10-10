"""API tests — run against a throwaway SQLite database.

    pytest
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402

TEST_DB = "/tmp/hiretrack_test.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

_test_engine = create_engine(
    f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False}
)
_TestingSession = sessionmaker(
    bind=_test_engine, autoflush=False, autocommit=False
)
Base.metadata.create_all(bind=_test_engine)


def _override_db():
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client():
    app = create_app()
    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    client.post(
        "/auth/register",
        json={"email": "dev@example.com", "password": "supersecret1"},
    )
    res = client.post(
        "/auth/token",
        data={"username": "dev@example.com", "password": "supersecret1"},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _make_app(client, headers, company="Acme", role="Backend Dev", **kw):
    payload = {"company": company, "role": role, **kw}
    res = client.post("/applications", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_register_duplicate_rejected(client):
    client.post(
        "/auth/register",
        json={"email": "dupe@example.com", "password": "supersecret1"},
    )
    res = client.post(
        "/auth/register",
        json={"email": "dupe@example.com", "password": "supersecret1"},
    )
    assert res.status_code == 400


def test_login_wrong_password_rejected(client):
    client.post(
        "/auth/register",
        json={"email": "wrongpw@example.com", "password": "supersecret1"},
    )
    res = client.post(
        "/auth/token",
        data={"username": "wrongpw@example.com", "password": "nope-nope-nope"},
    )
    assert res.status_code == 401


def test_unauthenticated_applications_rejected(client):
    assert client.get("/applications").status_code == 401
    assert (
        client.post(
            "/applications", json={"company": "X", "role": "Y"}
        ).status_code
        == 401
    )


def test_crud_lifecycle(client, auth_headers):
    created = _make_app(client, auth_headers, notes="first")
    app_id = created["id"]
    assert created["status"] == "wishlist"

    got = client.get(f"/applications/{app_id}", headers=auth_headers).json()
    assert got["company"] == "Acme"

    patched = client.patch(
        f"/applications/{app_id}",
        json={"status": "interviewing"},
        headers=auth_headers,
    ).json()
    assert patched["status"] == "interviewing"

    assert (
        client.delete(f"/applications/{app_id}", headers=auth_headers).status_code
        == 204
    )
    assert (
        client.get(f"/applications/{app_id}", headers=auth_headers).status_code
        == 404
    )


def test_list_filters_search_pagination(client, auth_headers):
    for i in range(5):
        _make_app(
            client,
            auth_headers,
            company=f"Company{i}",
            role="Backend Dev",
            status="applied" if i % 2 == 0 else "wishlist",
        )
    res = client.get(
        "/applications?status=applied", headers=auth_headers
    ).json()
    assert res["total"] == 3
    assert all(item["status"] == "applied" for item in res["items"])

    res = client.get("/applications?search=company1", headers=auth_headers).json()
    assert res["total"] == 1
    assert res["items"][0]["company"] == "Company1"

    res = client.get(
        "/applications?page=2&page_size=2", headers=auth_headers
    ).json()
    assert res["page"] == 2 and len(res["items"]) == 2


def test_users_cannot_see_each_others_data(client):
    client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "supersecret1"},
    )
    client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "supersecret1"},
    )
    alice = client.post(
        "/auth/token",
        data={"username": "alice@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    bob = client.post(
        "/auth/token",
        data={"username": "bob@example.com", "password": "supersecret1"},
    ).json()["access_token"]

    mine = _make_app(
        client, {"Authorization": f"Bearer {alice}"}, company="AliceCo"
    )
    res = client.get(
        f"/applications/{mine['id']}",
        headers={"Authorization": f"Bearer {bob}"},
    )
    assert res.status_code == 404
    res = client.get(
        "/applications", headers={"Authorization": f"Bearer {bob}"}
    ).json()
    assert res["total"] == 0


def test_stats_summary(client, auth_headers):
    _make_app(client, auth_headers, company="S1", status="applied")
    _make_app(client, auth_headers, company="S2", status="applied")
    _make_app(client, auth_headers, company="S3", status="rejected")
    res = client.get("/applications/stats/summary", headers=auth_headers).json()
    counts = {row["status"]: row["count"] for row in res}
    assert counts.get("applied", 0) >= 2
    assert counts.get("rejected", 0) >= 1
