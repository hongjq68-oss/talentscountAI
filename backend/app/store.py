"""Tiny JSON-file persistence for jobs and settings."""
import json
import os
import threading
from pathlib import Path

DATA_DIR = Path(os.environ.get("TSA_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
JOBS_DIR = DATA_DIR / "jobs"
SETTINGS_FILE = DATA_DIR / "settings.json"
JOBS_DIR.mkdir(parents=True, exist_ok=True)
_lock = threading.Lock()

SETTING_KEYS = [
    "OPENAI_API_KEY", "OPENAI_MODEL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
    "SERPER_API_KEY", "TAVILY_API_KEY", "BRAVE_API_KEY", "SERPAPI_API_KEY", "GITHUB_TOKEN",
]


def save_job(job: dict) -> None:
    with _lock:
        tmp = JOBS_DIR / f"{job['id']}.json.tmp"
        tmp.write_text(json.dumps(job, indent=2))
        tmp.replace(JOBS_DIR / f"{job['id']}.json")


def load_job(job_id: str) -> dict | None:
    p = JOBS_DIR / f"{job_id}.json"
    return json.loads(p.read_text()) if p.exists() else None


def list_jobs() -> list[dict]:
    jobs = [json.loads(p.read_text()) for p in JOBS_DIR.glob("*.json")]
    return sorted(jobs, key=lambda j: j.get("created_at", ""), reverse=True)


def delete_job(job_id: str) -> None:
    (JOBS_DIR / f"{job_id}.json").unlink(missing_ok=True)


def _stored_settings() -> dict:
    return json.loads(SETTINGS_FILE.read_text()) if SETTINGS_FILE.exists() else {}


def get_setting(key: str) -> str:
    return (_stored_settings().get(key) or os.environ.get(key) or "").strip()


def update_settings(values: dict) -> None:
    with _lock:
        cur = _stored_settings()
        for k, v in values.items():
            if k in SETTING_KEYS:
                if v:
                    cur[k] = v
                else:
                    cur.pop(k, None)
        SETTINGS_FILE.write_text(json.dumps(cur, indent=2))
        os.chmod(SETTINGS_FILE, 0o600)
