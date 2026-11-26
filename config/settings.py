"""Application settings and project paths."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "HospitaLytics"
TAGLINE = "Transforming Hospitality Software Requirements into Intelligent SDLC Decisions."
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
LLM_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
LLM_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
