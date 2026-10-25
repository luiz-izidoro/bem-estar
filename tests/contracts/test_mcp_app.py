from __future__ import annotations

import pytest

mcp = pytest.importorskip(
    "mcp", reason="MCP SDK v2 is resolved on the connected target environment"
)

from bemestar.infrastructure.config import Settings  # noqa: E402
from bemestar.interfaces.mcp.app import create_app  # noqa: E402


def test_mcp_v2_app_exposes_streamable_http_and_metadata(tmp_path) -> None:
    settings = Settings(
        env="test",
        database_url=f"sqlite:///{tmp_path / 'mcp.db'}",
        raw_dir=tmp_path / "raw",
        public_base_url="https://bemestar.example",
        webhook_token="webhook-token",
        mcp_token="mcp-token",
        session_secret="session-secret",
        dashboard_password_hash="not-used-in-this-test",
    )
    app = create_app(settings)
    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/mcp" in paths
    assert "/.well-known/oauth-protected-resource/mcp" in paths


def test_mcp_public_host_passes_transport_security_before_auth(tmp_path) -> None:
    """The production hostname must not be rejected with DNS-rebinding HTTP 421."""
    from starlette.testclient import TestClient

    settings = Settings(
        env="test",
        database_url=f"sqlite:///{tmp_path / 'mcp-host.db'}",
        raw_dir=tmp_path / "raw",
        public_base_url="https://bemestar.example",
        webhook_token="webhook-token",
        mcp_token="mcp-token",
        session_secret="session-secret",
        dashboard_password_hash="not-used-in-this-test",
    )
    app = create_app(settings)
    with TestClient(app, base_url="https://bemestar.example") as client:
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
            headers={"Mcp-Protocol-Version": "2026-07-28"},
        )
    assert response.status_code != 421
    assert response.status_code == 401
