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
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
# groq | gemini | offline. Empty = first provider with a key (Groq first).
LLM_PROVIDER = (os.getenv("ASTRACARE_LLM_PROVIDER") or ("groq" if GROQ_API_KEY else "gemini" if GEMINI_API_KEY else "offline")).lower()
DEFAULT_MODELS = {"groq": "qwen/qwen3.8-27b", "gemini": "gemini-2.5-flash"}
LLM_MODEL = os.getenv("ASTRACARE_LLM_MODEL") or DEFAULT_MODELS.get(LLM_PROVIDER, "")
# Groq reasoning models (Qwen): "hidden" drops the <think> trace from the answer; empty = provider default
GROQ_REASONING_FORMAT = os.getenv("ASTRACARE_GROQ_REASONING_FORMAT", "hidden")
# On HTTP 429, wait the provider's retry-after (when it is at most this many seconds) and try again
GROQ_RATE_LIMIT_RETRIES = int(_float("ASTRACARE_GROQ_RATE_LIMIT_RETRIES", 2))
GROQ_RATE_LIMIT_MAX_WAIT_S = _float("ASTRACARE_GROQ_RATE_LIMIT_MAX_WAIT_S", 8.0)
# Tools offered to the LLM (comma list, or "all"). Every round resends their schemas, and free tiers are small
# (Groq free: 8k tokens/minute on qwen/qwen3.8-27b), so the default is the monitoring chain + space weather + check-in.
DEFAULT_LLM_TOOLS = (
    "schedule_smartwatch_exam,analyze_telemetry_and_diagnose,trigger_central_alert,activate_psychological_stimuli,"
    "run_monitoring_cycle,check_nasa_donki_and_horizons_tool,log_sleep_mood_context_tool"
)
LLM_TOOLS = [t.strip() for t in os.getenv("ASTRACARE_LLM_TOOLS", DEFAULT_LLM_TOOLS).split(",") if t.strip()]
# Tool results longer than this are cut before going back to the model (the key fields come first)
LLM_TOOL_RESULT_MAX_CHARS = int(_float("ASTRACARE_LLM_TOOL_RESULT_MAX_CHARS", 1200))
LLM_MAX_TOOL_ROUNDS = int(_float("ASTRACARE_LLM_MAX_TOOL_ROUNDS", 5))
LLM_TIMEOUT_S = _float("ASTRACARE_LLM_TIMEOUT_S", 30.0)

# NASA DONKI + JPL Horizons refresh period, in minutes (each feed also keeps its own cache)
NASA_REFRESH_MIN = _float("ASTRACARE_NASA_REFRESH_MIN", 30.0)

# Autonomous smartwatch monitoring
SCHEDULER_ENABLED = _bool("ASTRACARE_SCHEDULER_ENABLED", True)
SCHEDULER_TICK_S = _float("ASTRACARE_SCHEDULER_TICK_S", 30.0)

# Central alerts: do not re-send the same diagnosis for the same astronaut inside this window
ALERT_COOLDOWN_MIN = _float("ASTRACARE_ALERT_COOLDOWN_MIN", 30.0)
