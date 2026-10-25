from __future__ import annotations

import logging
import signal
import time

from sqlalchemy.orm import Session, sessionmaker

from bemestar.adapters.notifications.providers import (
    NullNotificationProvider,
    WebhookNotificationProvider,
)
from bemestar.application.ingestion_service import IngestionProcessor
from bemestar.application.ports.notifications import NotificationProvider
from bemestar.application.repositories import Repository
from bemestar.infrastructure.config import Settings, get_settings
from bemestar.infrastructure.db import create_db_engine, make_session_factory
from bemestar.infrastructure.logging import configure_logging
from bemestar.infrastructure.telemetry import INGESTION_PROCESSED

logger = logging.getLogger(__name__)
_stop = False


def _stop_handler(_signum: int, _frame: object) -> None:
    global _stop
    _stop = True


def _notification_provider(settings: Settings) -> NotificationProvider:
    if settings.notification_webhook_url:
        return WebhookNotificationProvider(
            settings.notification_webhook_url, settings.notification_webhook_token
        )
    return NullNotificationProvider()


def run_once(factory: sessionmaker[Session], settings: Settings) -> bool:
    with factory() as session:
        ingestion = Repository(session).claim_next_ingestion(settings.worker_lease_seconds)
        if not ingestion:
            return False
        try:
            IngestionProcessor(session, settings).process(ingestion)
            INGESTION_PROCESSED.labels("processed").inc()
        except Exception as exc:
            INGESTION_PROCESSED.labels("failed").inc()
            try:
                _notification_provider(settings).send(
                    "Bem Estar ingestion failed",
                    f"Ingestion {ingestion.id} ({ingestion.stream}) failed: {type(exc).__name__}",
                    "error",
                )
            except Exception:
                logger.exception(
                    "failure notification could not be sent",
                    extra={"ingestion_id": ingestion.id},
                )
        return True


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings)
    factory = make_session_factory(engine)
    signal.signal(signal.SIGTERM, _stop_handler)
    signal.signal(signal.SIGINT, _stop_handler)
    logger.info("worker started")
    while not _stop:
        worked = run_once(factory, settings)
        if not worked:
            time.sleep(settings.worker_poll_seconds)
    logger.info("worker stopped")


if __name__ == "__main__":
    main()
