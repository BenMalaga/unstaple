from __future__ import annotations

import sys
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIXTURE_DIR))

from make_fixtures import build_all  # noqa: E402


@pytest.fixture(scope="session")
def fixture_pdfs() -> dict[str, Path]:
    """Synthetic stapled PDFs, regenerated if missing."""
    paths = {
        "basic": FIXTURE_DIR / "stapled_basic.pdf",
        "tricky": FIXTURE_DIR / "stapled_tricky.pdf",
    }
    if not all(p.is_file() for p in paths.values()):
        return build_all(FIXTURE_DIR)
    return paths
