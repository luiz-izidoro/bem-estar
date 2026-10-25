#!/usr/bin/env python3
"""Execute a command with a systemd-style EnvironmentFile without shell expansion.

This is deliberately used instead of `source /etc/bem-estar/bem-estar.env` because
PBKDF2 hashes and random secrets contain characters such as `$` that shells expand.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{lineno}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not key.replace("_", "").isalnum():
            raise ValueError(f"{path}:{lineno}: invalid variable name")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: run_with_env.py ENV_FILE COMMAND [ARGS...]")
    env_file = Path(sys.argv[1])
    command = sys.argv[2:]
    env = os.environ.copy()
    env.update(parse_env_file(env_file))
    os.execvpe(command[0], command, env)


if __name__ == "__main__":
    main()
