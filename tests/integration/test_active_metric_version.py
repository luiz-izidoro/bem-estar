from __future__ import annotations

from datetime import date

from bemestar.application.dashboard_service import DashboardService
from bemestar.application.repositories import Repository
from bemestar.infrastructure.config import Settings
from bemestar.infrastructure.db import Base, create_db_engine, make_session_factory


def test_dashboard_uses_explicit_active_metric_version(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}", raw_dir=tmp_path / "raw"
    )
    engine = create_db_engine(settings)
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as session:
        repo = Repository(session)
        repo.upsert_derived("readiness_live", "readiness-v1", "2026-09-15", 70, "score", {})
        repo.upsert_derived(
            "readiness_live", "readiness-v2-experimental", "2026-09-15", 99, "score", {}
        )
        session.commit()
        summary = DashboardService(session).day_summary(date(2026, 9, 15))
    assert summary["derived"]["readiness_live"] == 70
    assert summary["versions"]["readiness_live"] == "readiness-v1"
