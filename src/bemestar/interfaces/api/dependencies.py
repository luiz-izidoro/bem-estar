from __future__ import annotations

from collections.abc import Generator
from typing import cast

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, sessionmaker

from bemestar.infrastructure.config import Settings
from bemestar.infrastructure.security import verify_session


def get_settings_dep(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_session_factory(request: Request) -> sessionmaker[Session]:
    return cast(sessionmaker[Session], request.app.state.session_factory)


def get_db(
    factory: sessionmaker[Session] = Depends(get_session_factory),
) -> Generator[Session, None, None]:
    session = factory()
    try:
        yield session
    finally:
        session.close()


def require_user(
    request: Request, settings: Settings = Depends(get_settings_dep)
) -> dict[str, object]:
    token = request.cookies.get("bemestar_session")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required"
        )
    payload = verify_session(token, settings.session_secret)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired session"
        )
    return payload


def require_csrf(
    request: Request, user: dict[str, object] = Depends(require_user)
) -> dict[str, object]:
    header = request.headers.get("x-csrf-token")
    cookie = request.cookies.get("bemestar_csrf")
    expected = str(user.get("csrf") or "")
    if not header or not cookie or header != cookie or header != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
    return user
