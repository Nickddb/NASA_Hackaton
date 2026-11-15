"""
Runtime configuration. Every setting comes from an environment variable; for local work put them in
backend/.env (copy backend/.env.example). Real environment variables always win over the file, and the
file is never committed (.gitignore).
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env_file(path: Path = ENV_FILE) -> None:
    """Minimal KEY=VALUE reader (no extra dependency). Existing environment variables are not overridden."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


load_env_file()

# LLM (optional: without a key the agent runs the deterministic offline pipeline)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
LLM_MODEL = os.getenv("ASTRACARE_LLM_MODEL", "gemini-2.5-flash")
LLM_MAX_TOOL_ROUNDS = int(_float("ASTRACARE_LLM_MAX_TOOL_ROUNDS", 5))
LLM_TIMEOUT_S = _float("ASTRACARE_LLM_TIMEOUT_S", 12.0)

# Autonomous smartwatch monitoring
SCHEDULER_ENABLED = _bool("ASTRACARE_SCHEDULER_ENABLED", True)
SCHEDULER_TICK_S = _float("ASTRACARE_SCHEDULER_TICK_S", 30.0)

# Central alerts: do not re-send the same diagnosis for the same astronaut inside this window
ALERT_COOLDOWN_MIN = _float("ASTRACARE_ALERT_COOLDOWN_MIN", 30.0)
