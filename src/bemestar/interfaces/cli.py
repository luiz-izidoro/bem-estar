from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from bemestar.application.metrics_service import MetricsService
from bemestar.infrastructure.config import get_settings
from bemestar.infrastructure.db import create_db_engine, make_session_factory


def recompute_main() -> None:
    settings = get_settings()
    factory = make_session_factory(create_db_engine(settings))
    with factory() as session:
        local_today = datetime.now(ZoneInfo(settings.timezone)).date()
        result = MetricsService(session).recompute_all(through=local_today)
        session.commit()
    print(result)


if __name__ == "__main__":
    recompute_main()
