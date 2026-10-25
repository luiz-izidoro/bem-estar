from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    def generate_daily_insight(self, summary: dict[str, object], language: str) -> str: ...
