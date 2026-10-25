from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = Path(__file__).parents[2] / "scripts" / "run_with_env.py"
    spec = importlib.util.spec_from_file_location("bemestar_run_with_env", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_environment_file_parser_preserves_dollar_signs(tmp_path: Path) -> None:
    module = _load_module()
    env_file = tmp_path / "app.env"
    password_hash = "pbkdf2_sha256$600000$salt$hash"
    env_file.write_text(f"BEMESTAR_DASHBOARD_PASSWORD_HASH={password_hash}\nFOO='bar baz'\n")
    values = module.parse_env_file(env_file)
    assert values["BEMESTAR_DASHBOARD_PASSWORD_HASH"] == password_hash
    assert values["FOO"] == "bar baz"
