from __future__ import annotations

from pathlib import Path

from bemestar.infrastructure.config import Settings


def test_env_example_csv_lists_are_accepted(monkeypatch) -> None:
    """The documented `cp .env.example .env` path must parse CSV list values."""
    monkeypatch.delenv("BEMESTAR_TRUSTED_HOSTS", raising=False)
    monkeypatch.delenv("BEMESTAR_CORS_ORIGINS", raising=False)
    env_file = Path(__file__).resolve().parents[2] / ".env.example"

    settings = Settings(_env_file=env_file)

    assert settings.public_base_url == "http://localhost:8787"
    assert settings.trusted_hosts == ["localhost", "127.0.0.1"]
    assert settings.cors_origins == ["http://localhost:5173"]


def test_csv_lists_from_process_environment(monkeypatch) -> None:
    monkeypatch.setenv("BEMESTAR_TRUSTED_HOSTS", "localhost,example.com")
    monkeypatch.setenv("BEMESTAR_CORS_ORIGINS", "http://localhost:5173,https://example.com")

    settings = Settings(_env_file=None)

    assert settings.trusted_hosts == ["localhost", "example.com"]
    assert settings.cors_origins == ["http://localhost:5173", "https://example.com"]
