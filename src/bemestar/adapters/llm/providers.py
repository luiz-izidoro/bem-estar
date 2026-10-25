from __future__ import annotations

import json
import logging

import httpx

from bemestar.application.ports.llm import LLMProvider
from bemestar.infrastructure.config import Settings

logger = logging.getLogger(__name__)


def _format_metric(value: object, digits: int, suffix: str, decimal_sep: str) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}{suffix}".replace(".", decimal_sep)
    return "n/d" if decimal_sep == "," else "n/a"


class DeterministicInsightProvider(LLMProvider):
    def generate_daily_insight(self, summary: dict[str, object], language: str) -> str:
        metrics = summary.get("derived", {})
        if not isinstance(metrics, dict):
            metrics = {}
        if language.lower().startswith("pt"):
            readiness = _format_metric(metrics.get("readiness_live"), 0, "/100", ",")
            sleep = _format_metric(metrics.get("sleep_hours"), 1, " h", ",")
            return (
                f"Resumo determinístico: prontidão {readiness} · sono {sleep}. "
                "Use tendências de vários dias para decisões de treino; isto não é "
                "orientação médica."
            )
        readiness = _format_metric(metrics.get("readiness_live"), 0, "/100", ".")
        sleep = _format_metric(metrics.get("sleep_hours"), 1, " h", ".")
        return (
            f"Deterministic summary: readiness {readiness} · sleep {sleep}. "
            "Use multi-day trends for training decisions; this is not medical advice."
        )


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate_daily_insight(self, summary: dict[str, object], language: str) -> str:
        fallback = DeterministicInsightProvider()
        if not (
            self.settings.llm_base_url and self.settings.llm_api_key and self.settings.llm_model
        ):
            return fallback.generate_daily_insight(summary, language)
        system = (
            "You summarize personal wellness/training data conservatively. Do not diagnose, claim disease, "
            "or replace professional care. Distinguish observations from uncertainty. Keep it under 180 words. "
            f"Respond in {'Brazilian Portuguese' if language.lower().startswith('pt') else 'English'}."
        )
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        body = {
            "model": self.settings.llm_model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": "Summarize today's data:\n"
                    + json.dumps(summary, ensure_ascii=False),
                },
            ],
        }
        try:
            with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
                response = client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            logger.exception("LLM insight failed; returning deterministic fallback")
            return fallback.generate_daily_insight(summary, language)
