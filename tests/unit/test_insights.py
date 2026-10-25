from __future__ import annotations

from bemestar.adapters.llm.providers import DeterministicInsightProvider


def test_pt_insight_rounds_values() -> None:
    text = DeterministicInsightProvider().generate_daily_insight(
        {"derived": {"readiness_live": 45.594, "sleep_hours": 7.24}}, "pt-BR"
    )
    assert "prontidão 46/100" in text
    assert "sono 7,2 h" in text
    assert "45.594" not in text


def test_en_insight_rounds_values() -> None:
    text = DeterministicInsightProvider().generate_daily_insight(
        {"derived": {"readiness_live": 45.594, "sleep_hours": 7.24}}, "en"
    )
    assert "readiness 46/100" in text
    assert "sleep 7.2 h" in text
    assert "45.594" not in text


def test_insight_handles_missing_values() -> None:
    text = DeterministicInsightProvider().generate_daily_insight({"derived": {}}, "pt-BR")
    assert "prontidão n/d" in text
    assert "sono n/d" in text
