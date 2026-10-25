from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from bemestar.infrastructure.config import Settings
from bemestar.infrastructure.db import Base, create_db_engine
from bemestar.infrastructure.security import hash_password
from bemestar.interfaces.api.app import create_app

FIXTURE = Path(__file__).parents[1] / "fixtures" / "hae_v2_sample.json"


def test_canonical_and_compat_webhooks_accept_hae_v2(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'api.db'}"
    settings = Settings(
        env="test",
        database_url=db_url,
        raw_dir=tmp_path / "raw",
        webhook_token="test-webhook-token",
        mcp_token="test-mcp-token",
        session_secret="test-session-secret",
        dashboard_password_hash=hash_password("test-password-123"),
        trusted_hosts=["testserver"],
    )
    engine = create_db_engine(settings)
    Base.metadata.create_all(engine)
    engine.dispose()
    app = create_app(settings)
    payload = json.loads(FIXTURE.read_text())
    headers = {
        "Authorization": "Bearer test-webhook-token",
        "automation-id": "fixture-auto",
        "automation-name": "bemestar-history",
        "session-id": "fixture-session",
        "X-Bemestar-Stream": "history",
    }
    with TestClient(app) as client:
        first = client.post("/webhooks/hae/v2", json=payload, headers=headers)
        assert first.status_code == 202
        assert first.json()["duplicate"] is False
        duplicate = client.post("/webhooks/hae/v2", json=payload, headers=headers)
        assert duplicate.status_code == 202
        assert duplicate.json()["duplicate"] is True
        alias_headers = dict(headers)
        alias_headers["session-id"] = "fixture-session-2"
        alias = client.post("/v1/health-auto-export", json=payload, headers=alias_headers)
        assert alias.status_code == 202


def test_webhook_rejects_bad_token(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'api.db'}"
    settings = Settings(
        env="test",
        database_url=db_url,
        raw_dir=tmp_path / "raw",
        webhook_token="expected",
        mcp_token="mcp",
        session_secret="session",
        dashboard_password_hash=hash_password("test-password-123"),
        trusted_hosts=["testserver"],
    )
    engine = create_db_engine(settings)
    Base.metadata.create_all(engine)
    engine.dispose()
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/webhooks/hae/v2", json={"data": {}}, headers={"Authorization": "Bearer wrong"}
        )
    assert response.status_code == 401
