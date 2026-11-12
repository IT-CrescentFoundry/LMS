"""The package version is declared in two places; keep them in step."""

import tomllib

from app import __version__
from app.core.config import BACKEND_DIR


def test_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((BACKEND_DIR / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == __version__
