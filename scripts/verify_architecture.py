#!/usr/bin/env python3
"""Fail when source-layer imports violate the agreed dependency direction."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "bemestar"
RULES: dict[str, tuple[str, ...]] = {
    "domain": (
        "bemestar.application",
        "bemestar.adapters",
        "bemestar.infrastructure",
        "bemestar.interfaces",
    ),
    "application": ("bemestar.interfaces",),
}


def imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.append(node.module)
    return result


def main() -> None:
    failures: list[str] = []
    for layer, forbidden_prefixes in RULES.items():
        for path in (ROOT / layer).rglob("*.py"):
            for name in imports(path):
                if name.startswith(forbidden_prefixes):
                    failures.append(f"{path.relative_to(ROOT.parent)} imports forbidden {name}")
    if failures:
        print("Architecture violations:")
        print("\n".join(f" - {item}" for item in failures))
        raise SystemExit(1)
    print("Architecture dependency rules: OK")


if __name__ == "__main__":
    main()
