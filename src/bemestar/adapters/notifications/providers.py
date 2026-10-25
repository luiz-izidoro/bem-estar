from __future__ import annotations

import httpx

from bemestar.application.ports.notifications import NotificationProvider


class NullNotificationProvider(NotificationProvider):
    def send(self, title: str, message: str, severity: str = "info") -> None:
        return None


class WebhookNotificationProvider(NotificationProvider):
    def __init__(self, url: str, token: str = ""):
        self.url = url
        self.token = token

    def send(self, title: str, message: str, severity: str = "info") -> None:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        httpx.post(
            self.url,
            json={"title": title, "message": message, "severity": severity},
            headers=headers,
            timeout=10,
        ).raise_for_status()
