"""Ensure the repo root is importable so tests can ``import config``, ``model``,
``simulation``, and ``scripts`` regardless of how pytest is invoked."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
