"""Single entry point for reading ``config.yaml`` (§6.7).

Every module — model training, simulation, the pipeline — reads its knobs from
here so there are no magic numbers in code. Also provides a stable hash of the
resolved config for the run manifest, so two runs can be diffed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

# Repo root = directory containing this file.
ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT / "config.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load and return the YAML config as a plain dict."""
    cfg_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ValueError(f"Config at {cfg_path} did not parse to a mapping.")
    return cfg


def config_hash(cfg: dict[str, Any]) -> str:
    """Stable short hash of a config dict for the run manifest.

    Uses a canonical JSON encoding (sorted keys) so the hash is independent of
    YAML key ordering or formatting.
    """
    canonical = json.dumps(cfg, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def resolve_path(relative: str | Path) -> Path:
    """Resolve a config-relative path against the repo root."""
    p = Path(relative)
    return p if p.is_absolute() else (ROOT / p)
