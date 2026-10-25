from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import shutil
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

import orjson
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func, select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from starlette.middleware.base import RequestResponseEndpoint

from bemestar.adapters.hae.raw_store import RawStore
from bemestar.adapters.llm.providers import OpenAICompatibleProvider
from bemestar.application.dashboard_service import DashboardService
from bemestar.application.metrics_service import MetricsService
from bemestar.application.repositories import Repository
from bemestar.infrastructure.config import Settings, get_settings
from bemestar.infrastructure.db import create_db_engine, make_session_factory
from bemestar.infrastructure.logging import configure_logging
from bemestar.infrastructure.models import IngestionRequest
from bemestar.infrastructure.security import (
    MemoryRateLimiter,
    RateRule,
    create_session,
    verify_password,
)
from bemestar.infrastructure.telemetry import (
    HTTP_LATENCY,
    HTTP_REQUESTS,
    INGESTION_PENDING,
    INGESTION_RECEIVED,
)
from bemestar.interfaces.api.dependencies import get_db, require_csrf, require_user
from bemestar.interfaces.api.schemas import LoginRequest, ProfileUpdate

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    # Caddy is the only intended public ingress. It overwrites/sets X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _metric_path_hint(path: str) -> str:
    if path.startswith("/auth/"):
        return "/auth/*"
    if path.startswith("/api/"):
        return "/api/*"
    if path.startswith("/webhooks/") or path == "/v1/health-auto-export":
        return "/webhooks/*"
    if path in {"/healthz", "/readyz", "/metrics"}:
        return path
    return "/unmatched"


def _infer_stream(payload: dict[str, Any], header: str | None, automation_name: str | None) -> str:
    allowed = {"vitals", "activity", "sleep", "workouts", "history", "reconciliation"}
    if header and header.lower() in allowed:
        return header.lower()
    data = payload.get("data") or {}
    if isinstance(data, dict) and data.get("workouts"):
        return "workouts"
    name = (automation_name or "").lower()
    for value in allowed:
        if value in name:
            return value
    return "vitals"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings)
    session_factory = make_session_factory(engine)
    limiter = MemoryRateLimiter(settings.rate_limiter_max_keys)
    raw_store = RawStore(settings.raw_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.limiter = limiter
        yield
        engine.dispose()

    app = FastAPI(
        title="Bem Estar API",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.env != "production" else None,
        redoc_url=None,
    )
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts, www_redirect=False
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Authorization", "X-Bemestar-Stream"],
    )

    @app.middleware("http")
    async def security_and_metrics(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        started = time.monotonic()
        path = request.url.path
        ip = _client_ip(request)
        if path.startswith("/auth/login"):
            rule = RateRule(settings.login_rate_limit, settings.login_rate_window_seconds)
            bucket = f"login:{ip}"
        elif path in {"/webhooks/hae/v2", "/v1/health-auto-export"}:
            rule = RateRule(settings.webhook_rate_limit, settings.webhook_rate_window_seconds)
            bucket = f"hae:{ip}"
        else:
            rule = RateRule(settings.api_rate_limit, settings.api_rate_window_seconds)
            bucket = f"api:{ip}"
        if not limiter.allow(bucket, rule):
            HTTP_REQUESTS.labels(request.method, _metric_path_hint(path), "429").inc()
            return Response(
                content='{"detail":"rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(rule.window_seconds)},
            )
        response = await call_next(request)
        elapsed = time.monotonic() - started
        route = request.scope.get("route")
        metric_path = getattr(route, "path", None) or (
            "/webhooks/*" if path.startswith("/webhooks/") else "/unmatched"
        )
        HTTP_LATENCY.labels(metric_path).observe(elapsed)
        HTTP_REQUESTS.labels(request.method, metric_path, str(response.status_code)).inc()
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz(db: Session = Depends(get_db)) -> dict[str, object]:
        db.execute(text("SELECT 1"))
        free_bytes = shutil.disk_usage(settings.raw_dir).free
        if free_bytes < settings.min_free_disk_bytes:
            raise HTTPException(status_code=503, detail="insufficient free disk space")
        return {"status": "ready", "storage": "ok"}

    @app.get("/metrics", include_in_schema=False)
    def prometheus_metrics() -> Response:
        with session_factory() as session:
            pending = (
                session.scalar(
                    select(func.count())
                    .select_from(IngestionRequest)
                    .where(IngestionRequest.status == "pending")
                )
                or 0
            )
            INGESTION_PENDING.set(pending)
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/auth/login")
    def login(body: LoginRequest, response: Response) -> dict[str, object]:
        # Always perform the expensive password verification to reduce username timing leakage.
        password_ok = verify_password(body.password, settings.dashboard_password_hash)
        username_ok = hmac.compare_digest(body.username, settings.dashboard_username)
        if not (username_ok and password_ok):
            raise HTTPException(status_code=401, detail="invalid credentials")
        token, csrf = create_session(
            body.username, settings.session_secret, settings.session_ttl_seconds
        )
        secure = settings.public_base_url.startswith("https://")
        response.set_cookie(
            "bemestar_session",
            token,
            httponly=True,
            secure=secure,
            samesite="lax",
            max_age=settings.session_ttl_seconds,
            path="/",
        )
        response.set_cookie(
            "bemestar_csrf",
            csrf,
            httponly=False,
            secure=secure,
            samesite="lax",
            max_age=settings.session_ttl_seconds,
            path="/",
        )
        return {"ok": True, "user": body.username}

    @app.post("/auth/logout")
    def logout(
        response: Response, _user: dict[str, object] = Depends(require_csrf)
    ) -> dict[str, bool]:
        response.delete_cookie("bemestar_session", path="/")
        response.delete_cookie("bemestar_csrf", path="/")
        return {"ok": True}

    @app.get("/api/v1/me")
    def me(user: dict[str, object] = Depends(require_user)) -> dict[str, object]:
        return {"username": user["sub"]}

    def local_today() -> date:
        return datetime.now(ZoneInfo(settings.timezone)).date()

    async def receive_hae(request: Request, db: Session) -> dict[str, object]:
        auth = request.headers.get("authorization", "")
        if not hmac.compare_digest(auth, f"Bearer {settings.webhook_token}"):
            raise HTTPException(status_code=401, detail="invalid webhook token")
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="invalid Content-Length") from exc
            if declared_size > settings.max_webhook_bytes:
                raise HTTPException(
                    status_code=413, detail="payload too large; enable HAE batch requests"
                )
        if shutil.disk_usage(settings.raw_dir).free < settings.min_free_disk_bytes:
            raise HTTPException(status_code=507, detail="insufficient storage for health export")
        chunks: list[bytes] = []
        received = 0
        async for chunk in request.stream():
            received += len(chunk)
            if received > settings.max_webhook_bytes:
                raise HTTPException(
                    status_code=413, detail="payload too large; enable HAE batch requests"
                )
            chunks.append(chunk)
        raw = b"".join(chunks)
        try:
            payload = await asyncio.to_thread(orjson.loads, raw)
        except orjson.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
            raise HTTPException(
                status_code=422, detail="expected HAE JSON envelope with data object"
            )
        automation_id = request.headers.get("automation-id")
        automation_name = request.headers.get("automation-name")
        session_id = request.headers.get("session-id")
        stream = _infer_stream(payload, request.headers.get("x-bemestar-stream"), automation_name)
        digest = hashlib.sha256(raw).hexdigest()
        idempotency_key = hashlib.sha256(
            f"{automation_id or 'unknown'}|{stream}|{digest}".encode()
        ).hexdigest()
        repo = Repository(db)
        existing = repo.get_ingestion_by_key(idempotency_key)
        if existing:
            return {
                "accepted": True,
                "duplicate": True,
                "ingestion_id": existing.id,
                "status": existing.status,
            }
        path = await asyncio.to_thread(raw_store.write, raw, digest, stream)
        ingestion_id = str(uuid.uuid4())
        values = {
            "id": ingestion_id,
            "idempotency_key": idempotency_key,
            "automation_id": automation_id,
            "automation_name": automation_name,
            "automation_period": request.headers.get("automation-period"),
            "automation_aggregation": request.headers.get("automation-aggregation"),
            "session_id": session_id,
            "stream": stream,
            "payload_hash": digest,
            "payload_size": len(raw),
            "raw_path": str(path),
            "status": "pending",
        }
        insert_stmt = (
            sqlite_insert(IngestionRequest)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[IngestionRequest.idempotency_key])
        )
        result = db.execute(insert_stmt)
        db.commit()
        if not cast(CursorResult[Any], result).rowcount:
            existing = repo.get_ingestion_by_key(idempotency_key)
            if existing is None:
                raise HTTPException(
                    status_code=409, detail="idempotency race could not be resolved"
                )
            return {
                "accepted": True,
                "duplicate": True,
                "ingestion_id": existing.id,
                "status": existing.status,
            }
        INGESTION_RECEIVED.labels(stream).inc()
        return {
            "accepted": True,
            "duplicate": False,
            "ingestion_id": ingestion_id,
            "status": "pending",
        }

    @app.post("/webhooks/hae/v2", status_code=status.HTTP_202_ACCEPTED)
    async def hae_v2(request: Request, db: Session = Depends(get_db)) -> dict[str, object]:
        return await receive_hae(request, db)

    @app.post(
        "/v1/health-auto-export", status_code=status.HTTP_202_ACCEPTED, include_in_schema=False
    )
    async def hae_compat(request: Request, db: Session = Depends(get_db)) -> dict[str, object]:
        return await receive_hae(request, db)

    @app.get("/api/v1/dashboard/today")
    def dashboard_today(
        day: date | None = None,
        db: Session = Depends(get_db),
        _user: dict[str, object] = Depends(require_user),
    ) -> dict[str, object]:
        return DashboardService(db).day_summary(day or local_today())

    @app.get("/api/v1/metrics/{metric}")
    def metric_history(
        metric: str,
        days: int = 30,
        db: Session = Depends(get_db),
        _user: dict[str, object] = Depends(require_user),
    ) -> list[dict[str, object]]:
        if days < 1 or days > 730:
            raise HTTPException(status_code=422, detail="days must be between 1 and 730")
        return DashboardService(db).metric_history(metric, days, end=local_today())

    @app.get("/api/v1/workouts")
    def workouts(
        days: int = 30,
        db: Session = Depends(get_db),
        _user: dict[str, object] = Depends(require_user),
    ) -> list[dict[str, object]]:
        end = local_today()
        start = date.fromordinal(end.toordinal() - max(1, days) + 1)
        result = Repository(db).workouts_between(start.isoformat(), end.isoformat())
        return [
            {
                "id": w.external_id,
                "name": w.name,
                "start": w.start_utc,
                "duration_seconds": w.duration_seconds,
                "distance_km": w.distance_km,
                "avg_hr": w.avg_hr,
                "max_hr": w.max_hr,
            }
            for w in reversed(result)
        ]

    @app.get("/api/v1/ingestions")
    def ingestions(
        limit: int = 20,
        db: Session = Depends(get_db),
        _user: dict[str, object] = Depends(require_user),
    ) -> list[dict[str, object]]:
        rows = Repository(db).recent_ingestions(min(max(limit, 1), 100))
        return [
            {
                "id": r.id,
                "received_at": r.received_at,
                "stream": r.stream,
                "status": r.status,
                "records_received": r.records_received,
                "records_inserted": r.records_inserted,
                "records_ignored": r.records_ignored,
                "error": r.error,
            }
            for r in rows
        ]

    @app.post("/api/v1/admin/recompute")
    def recompute(
        db: Session = Depends(get_db), _user: dict[str, object] = Depends(require_csrf)
    ) -> dict[str, int]:
        result = MetricsService(db).recompute_all(through=local_today())
        db.commit()
        return result

    @app.get("/api/v1/settings/profile")
    def get_profile(
        db: Session = Depends(get_db), _user: dict[str, object] = Depends(require_user)
    ) -> dict[str, object]:
        p = Repository(db).profile()
        return {
            "hr_max": p.hr_max,
            "hr_rest": p.hr_rest,
            "trimp_exponential_coefficient": p.trimp_exponential_coefficient,
            "target_sleep_hours": p.target_sleep_hours,
            "locale": p.locale,
        }

    @app.put("/api/v1/settings/profile")
    def update_profile(
        body: ProfileUpdate,
        db: Session = Depends(get_db),
        _user: dict[str, object] = Depends(require_csrf),
    ) -> dict[str, object]:
        p = Repository(db).profile()
        for key, value in body.model_dump().items():
            setattr(p, key, value)
        db.commit()
        return body.model_dump()

    @app.get("/api/v1/insights/daily")
    def daily_insight(
        language: str = "pt-BR",
        db: Session = Depends(get_db),
        _user: dict[str, object] = Depends(require_user),
    ) -> dict[str, str]:
        summary = DashboardService(db).day_summary(local_today())
        provider = OpenAICompatibleProvider(settings)
        return {
            "insight": provider.generate_daily_insight(summary, language),
            "provider": "openai-compatible" if settings.llm_base_url else "deterministic",
        }

    return app
