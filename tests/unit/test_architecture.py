from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_architecture_import_rules() -> None:
    root = Path(__file__).parents[2]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "verify_architecture.py")], cwd=root, check=False
    )
    assert result.returncode == 0
