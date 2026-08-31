from pathlib import Path

from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = ROOT_DIR / "data"
JOBS_DIR = DATA_DIR / "jobs"
GENERATED_DIR = DATA_DIR / "generated"
SESSIONS_DIR = DATA_DIR / "sessions"

PROFILE_PATH = DATA_DIR / "profile.json"
QA_BANK_PATH = DATA_DIR / "qa_bank.json"
TRACKER_DB_PATH = DATA_DIR / "tracker.db"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")

# LLM_BACKEND lets you force "anthropic" or "ollama" explicitly via .env.
# Left unset, it auto-picks: Anthropic if a key is present, otherwise the
# free local Ollama model.
LLM_BACKEND = os.environ.get("LLM_BACKEND") or ("anthropic" if ANTHROPIC_API_KEY else "ollama")

LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs/"
NAUKRI_LOGIN_URL = "https://www.naukri.com/nlogin/login"
NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"


def ensure_dirs() -> None:
    for d in (DATA_DIR, JOBS_DIR, GENERATED_DIR, SESSIONS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def require_api_key() -> str:
    if not ANTHROPIC_API_KEY:
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key, "
            "or set LLM_BACKEND=ollama in .env to use the free local model instead."
        )
    return ANTHROPIC_API_KEY
