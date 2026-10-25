from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_alembic_head_matches_sqlalchemy_metadata(tmp_path: Path) -> None:
    """A clean database migrated to head must have zero autogenerate drift."""
    root = Path(__file__).parents[2]
    database = tmp_path / "migration-check.db"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    env["BEMESTAR_DATABASE_URL"] = f"sqlite:///{database}"
    env["BEMESTAR_RAW_DIR"] = str(tmp_path / "raw")

    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr

    check = subprocess.run(
        [sys.executable, "-m", "alembic", "check"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert check.returncode == 0, check.stdout + check.stderr
    assert "No new upgrade operations detected" in (check.stdout + check.stderr)
