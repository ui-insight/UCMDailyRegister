import pytest
from pydantic import ValidationError

from app.config import Settings


def test_cors_origins_accept_comma_separated_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:5173, https://ucmnews.insight.uidaho.edu",
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:5173",
        "https://ucmnews.insight.uidaho.edu",
    ]


def test_cors_origins_accept_json_array_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        '["http://localhost:5173", "https://ucmnews.insight.uidaho.edu"]',
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:5173",
        "https://ucmnews.insight.uidaho.edu",
    ]


def test_production_requires_explicit_cors_origins(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    with pytest.raises(ValidationError, match="CORS_ORIGINS must be set"):
        Settings(_env_file=None)


def test_production_rejects_wildcard_cors_origin(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", '["*"]')

    with pytest.raises(ValidationError, match="cannot include"):
        Settings(_env_file=None)
