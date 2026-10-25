#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import secrets

ITERATIONS = 600_000


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    salt_b64 = base64.urlsafe_b64encode(salt).decode()
    digest_b64 = base64.urlsafe_b64encode(digest).decode()
    return f"pbkdf2_sha256${ITERATIONS}${salt_b64}${digest_b64}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Bem Estar production secrets")
    parser.add_argument("--password", help="Dashboard password (prompted if omitted)")
    parser.add_argument(
        "--password-hash-only",
        action="store_true",
        help="Print only BEMESTAR_DASHBOARD_PASSWORD_HASH",
    )
    args = parser.parse_args()
    password = args.password or getpass.getpass("Dashboard password: ")
    if len(password) < 12:
        raise SystemExit("Use a dashboard password with at least 12 characters.")
    password_value = password_hash(password)
    if args.password_hash_only:
        print(f"BEMESTAR_DASHBOARD_PASSWORD_HASH={password_value}")
        return
    values = {
        "BEMESTAR_WEBHOOK_TOKEN": secrets.token_urlsafe(48),
        "BEMESTAR_MCP_TOKEN": secrets.token_urlsafe(48),
        "BEMESTAR_SESSION_SECRET": secrets.token_urlsafe(64),
        "BEMESTAR_DASHBOARD_PASSWORD_HASH": password_value,
    }
    for key, value in values.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
