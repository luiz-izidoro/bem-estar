from __future__ import annotations

import hmac
from datetime import date, datetime, timedelta
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl

from bemestar.application.dashboard_service import DashboardService
from bemestar.application.metrics_service import MetricsService
from bemestar.application.repositories import Repository
from bemestar.infrastructure.config import Settings, get_settings
from bemestar.infrastructure.db import create_db_engine, make_session_factory


class StaticTokenVerifier(TokenVerifier):
    """Bootstrap verifier for personal clients that support a pre-configured bearer token.

    For automatic OAuth discovery/login in clients that require it, replace this adapter with a real OAuth 2.1 identity provider verifier; the MCP server code remains unchanged.
    """

    def __init__(self, token: str, resource: str):
        self._token = token
        self._resource = resource

    async def verify_token(self, token: str) -> AccessToken | None:
        if hmac.compare_digest(token, self._token):
            return AccessToken(
                token=token,
                client_id="bemestar-personal-client",
                scopes=["health:read", "health:compute"],
                resource=self._resource,
            )
        return None


def create_app(settings: Settings | None = None):
    settings = settings or get_settings()
    engine = create_db_engine(settings)
    factory = make_session_factory(engine)
    public_base = settings.public_base_url.rstrip("/")
    resource_url = public_base + "/mcp"
    parsed_public = urlparse(public_base)
    public_host = parsed_public.hostname or "localhost"
    public_origin = (
        f"{parsed_public.scheme}://{parsed_public.netloc}"
        if parsed_public.scheme and parsed_public.netloc
        else public_base
    )
    transport_security = TransportSecuritySettings(
        allowed_hosts=[
            public_host,
            f"{public_host}:*",
            "localhost",
            "localhost:*",
            "127.0.0.1",
            "127.0.0.1:*",
        ],
        allowed_origins=[
            public_origin,
            "http://localhost:*",
            "http://127.0.0.1:*",
        ],
    )

    def local_today() -> date:
        return datetime.now(ZoneInfo(settings.timezone)).date()

    # Static-token bootstrap follows the official SDK's TokenVerifier contract. The issuer URL is metadata only until a real OAuth AS is configured.
    mcp = MCPServer(
        "Bem Estar",
        title="Bem Estar Personal Health",
        description="Private Apple Health analytics and training/recovery context.",
        instructions="Use deterministic data as evidence. Do not infer diagnoses or present this service as medical care.",
        version="0.2.0",
        token_verifier=StaticTokenVerifier(settings.mcp_token, resource_url),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(settings.public_base_url.rstrip("/") + "/"),
            resource_server_url=AnyHttpUrl(resource_url),
            required_scopes=["health:read"],
            validate_token_resource=False,
        ),
    )

    @mcp.tool()
    def get_health_summary(day: str | None = None) -> dict[str, object]:
        """Get canonical and derived health/training summary for an ISO date (YYYY-MM-DD)."""
        target = date.fromisoformat(day) if day else local_today()
        with factory() as session:
            return DashboardService(session).day_summary(target)

    @mcp.tool()
    def get_metric_history(metric: str, days: int = 30) -> list[dict[str, object]]:
        """Return raw or derived history for one metric over the requested number of days."""
        if days < 1 or days > 730:
            raise ValueError("days must be between 1 and 730")
        with factory() as session:
            return DashboardService(session).metric_history(metric, days, end=local_today())

    @mcp.tool()
    def analyze_sleep(day: str | None = None) -> dict[str, object]:
        """Return the sleep and readiness components for a day without generating medical conclusions."""
        target = date.fromisoformat(day) if day else local_today()
        with factory() as session:
            summary = DashboardService(session).day_summary(target)
        derived = summary.get("derived", {})
        components = summary.get("components", {})
        return {
            "date": target.isoformat(),
            "sleep_hours": derived.get("sleep_hours") if isinstance(derived, dict) else None,
            "sleep_efficiency_score": derived.get("sleep_efficiency_score")
            if isinstance(derived, dict)
            else None,
            "readiness_morning": derived.get("readiness_morning")
            if isinstance(derived, dict)
            else None,
            "components": components.get("readiness_morning")
            if isinstance(components, dict)
            else None,
        }

    @mcp.tool()
    def analyze_training_load(day: str | None = None) -> dict[str, object]:
        """Return TRIMP-derived training load, CTL, ATL, TSB and ACWR for a day."""
        target = date.fromisoformat(day) if day else local_today()
        with factory() as session:
            summary = DashboardService(session).day_summary(target)
        d = summary.get("derived", {})
        if not isinstance(d, dict):
            return {"date": target.isoformat()}
        return {
            "date": target.isoformat(),
            **{k: d.get(k) for k in ("training_load", "ctl", "atl", "tsb", "acwr")},
        }

    @mcp.tool()
    def analyze_workouts(days: int = 14) -> list[dict[str, object]]:
        """List recent workouts with duration, distance and heart-rate summary."""
        if days < 1 or days > 365:
            raise ValueError("days must be between 1 and 365")
        end = local_today()
        start = end - timedelta(days=days - 1)
        with factory() as session:
            rows = Repository(session).workouts_between(start.isoformat(), end.isoformat())
        return [
            {
                "id": w.external_id,
                "date": w.local_date,
                "name": w.name,
                "duration_seconds": w.duration_seconds,
                "distance_km": w.distance_km,
                "avg_hr": w.avg_hr,
                "max_hr": w.max_hr,
            }
            for w in rows
        ]

    @mcp.tool()
    def compare_periods(
        metric: str, current_days: int = 7, previous_days: int = 7
    ) -> dict[str, object]:
        """Compare average values for a metric across adjacent current and previous periods."""
        if min(current_days, previous_days) < 1 or current_days + previous_days > 730:
            raise ValueError("periods must be positive and total <= 730 days")
        with factory() as session:
            svc = DashboardService(session)
            data = svc.metric_history(metric, current_days + previous_days, end=local_today())
        # Raw metrics can contain many points per day. Aggregate to one daily median
        # before comparing calendar periods so high-frequency days are not overweighted.
        from statistics import median

        by_day: dict[str, list[float]] = {}
        for item in data:
            value = item.get("value")
            day_key = item.get("date")
            if isinstance(value, (int, float)) and isinstance(day_key, str):
                by_day.setdefault(day_key, []).append(float(value))
        daily = [(day_key, float(median(values))) for day_key, values in sorted(by_day.items())]
        current = daily[-current_days:]
        previous = daily[-(current_days + previous_days) : -current_days]

        def avg(rows: list[tuple[str, float]]) -> float | None:
            nums = [value for _, value in rows]
            return sum(nums) / len(nums) if nums else None

        current_avg = avg(current)
        previous_avg = avg(previous)
        change = (
            None
            if current_avg is None or previous_avg in {None, 0}
            else (current_avg - previous_avg) / previous_avg * 100.0
        )
        return {
            "metric": metric,
            "current_average": current_avg,
            "previous_average": previous_avg,
            "change_percent": change,
            "current_days": len(current),
            "previous_days": len(previous),
        }

    @mcp.tool()
    def get_ingestion_status(limit: int = 10) -> list[dict[str, object]]:
        """Inspect recent HAE ingestion jobs and failures without exposing raw payloads."""
        with factory() as session:
            rows = Repository(session).recent_ingestions(max(1, min(limit, 50)))
        return [
            {
                "id": r.id,
                "received_at": r.received_at,
                "stream": r.stream,
                "status": r.status,
                "records_received": r.records_received,
                "records_inserted": r.records_inserted,
                "error": r.error,
            }
            for r in rows
        ]

    @mcp.tool()
    def recompute_metrics() -> dict[str, int]:
        """Recompute deterministic derived metrics after a profile/formula configuration change."""
        with factory() as session:
            result = MetricsService(session).recompute_all(through=local_today())
            session.commit()
        return result

    @mcp.resource("bemestar://today", mime_type="application/json")
    def today_resource() -> dict[str, object]:
        """Today's health/recovery/training context."""
        with factory() as session:
            return DashboardService(session).day_summary(local_today())

    @mcp.resource("bemestar://day/{day}", mime_type="application/json")
    def day_resource(day: str) -> dict[str, object]:
        """Health/recovery/training context for one ISO date."""
        with factory() as session:
            return DashboardService(session).day_summary(date.fromisoformat(day))

    @mcp.resource("bemestar://metric/{metric}", mime_type="application/json")
    def metric_resource(metric: str) -> list[dict[str, object]]:
        """Last 30 days of a metric."""
        with factory() as session:
            return DashboardService(session).metric_history(metric, 30, end=local_today())

    @mcp.prompt()
    def daily_review(language: str = "pt-BR") -> str:
        """Review today's sleep, recovery, readiness and training balance."""
        lang = "Brazilian Portuguese" if language.lower().startswith("pt") else "English"
        return f"Read bemestar://today and provide a concise daily review in {lang}. Separate observations from interpretation. Mention missing data. Do not diagnose or provide medical treatment advice."

    @mcp.prompt()
    def weekly_training_review(language: str = "pt-BR") -> str:
        """Review the last week of training load and recovery versus recent history."""
        lang = "Brazilian Portuguese" if language.lower().startswith("pt") else "English"
        return f"Use get_metric_history for training_load, ctl, atl, tsb, acwr, readiness_live and sleep_hours over at least 28 days, then summarize the most recent week in {lang}. Prefer trends over single-day values and explicitly state uncertainty."

    @mcp.prompt()
    def sleep_review(language: str = "pt-BR") -> str:
        """Review sleep duration/efficiency and relationship to recovery trends."""
        lang = "Brazilian Portuguese" if language.lower().startswith("pt") else "English"
        return f"Use sleep_hours, sleep_efficiency_score, heart_rate_variability, resting_heart_rate and recovery history to summarize sleep/recovery trends in {lang}. Do not make diagnostic claims."

    return mcp.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        host="127.0.0.1",
        transport_security=transport_security,
    )
