from pathlib import Path

import pytest

from oilgas.database import Database
from oilgas.web import create_app
from oilgas.web.auth import authentication_settings


def test_production_authentication_requires_all_secrets(monkeypatch) -> None:
    monkeypatch.setenv("OILGAS_AUTH_REQUIRED", "true")
    monkeypatch.delenv("OILGAS_SECRET_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("OILGAS_ALLOWED_EMAILS", raising=False)

    with pytest.raises(RuntimeError, match="OILGAS_SECRET_KEY"):
        authentication_settings()


def test_protected_app_redirects_unauthenticated_requests(tmp_path, monkeypatch) -> None:
    database_path = Path(tmp_path) / "oilgas.duckdb"
    database = Database(database_path)
    database.initialize()
    database.close()

    monkeypatch.setenv("OILGAS_AUTH_REQUIRED", "true")
    monkeypatch.setenv("OILGAS_SECRET_KEY", "test-secret")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("OILGAS_ALLOWED_EMAILS", "travis@example.com")

    response = create_app(database_path).test_client().get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_owner_revenue_route_and_csv_export_are_available(tmp_path, monkeypatch) -> None:
    database_path = Path(tmp_path) / "oilgas.duckdb"
    database = Database(database_path)
    database.initialize()
    database.close()
    monkeypatch.setenv("OILGAS_AUTH_REQUIRED", "false")

    client = create_app(database_path).test_client()

    page = client.get("/owner-revenue")
    export = client.get("/export/owner_revenue.csv")

    assert page.status_code == 200
    assert b"Owner revenue by property and product" in page.data
    assert b"Owner revenue" in page.data
    assert export.status_code == 200
    assert export.mimetype == "text/csv"
    assert b"product_category" in export.data


def test_google_callback_is_safe_when_authentication_is_disabled(tmp_path, monkeypatch) -> None:
    database_path = Path(tmp_path) / "oilgas.duckdb"
    database = Database(database_path)
    database.initialize()
    database.close()
    monkeypatch.setenv("OILGAS_AUTH_REQUIRED", "false")

    response = create_app(database_path).test_client().get("/auth/google/callback")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
