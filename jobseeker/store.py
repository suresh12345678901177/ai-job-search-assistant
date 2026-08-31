import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import config


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "job"


def load_profile() -> dict:
    if not config.PROFILE_PATH.exists():
        raise FileNotFoundError(
            "No profile.json found. Run `ingest-resume <path>` first."
        )
    with open(config.PROFILE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_profile(profile: dict) -> None:
    config.ensure_dirs()
    with open(config.PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


def new_job_id(company: str, title: str) -> str:
    base = _slugify(f"{company}-{title}")[:50]
    suffix = uuid.uuid4().hex[:6]
    return f"{base}-{suffix}"


def save_job(job: dict) -> str:
    config.ensure_dirs()
    job_id = job.get("id") or new_job_id(job.get("company", ""), job.get("title", ""))
    job["id"] = job_id
    job.setdefault("saved_at", datetime.now(timezone.utc).isoformat())
    path = config.JOBS_DIR / f"{job_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(job, f, indent=2, ensure_ascii=False)
    return job_id


def load_job(job_id: str) -> dict:
    path = config.JOBS_DIR / f"{job_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No saved job with id '{job_id}'")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_jobs() -> list[dict]:
    config.ensure_dirs()
    jobs = []
    for path in sorted(config.JOBS_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            jobs.append(json.load(f))
    return jobs


def load_qa_bank() -> list[dict]:
    if not config.QA_BANK_PATH.exists():
        return []
    with open(config.QA_BANK_PATH, encoding="utf-8") as f:
        return json.load(f)


def add_qa_entry(question: str, answer: str, job_id: str, job_title: str, company: str) -> None:
    config.ensure_dirs()
    bank = load_qa_bank()
    bank.append(
        {
            "question": question,
            "answer": answer,
            "job_id": job_id,
            "job_title": job_title,
            "company": company,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    with open(config.QA_BANK_PATH, "w", encoding="utf-8") as f:
        json.dump(bank, f, indent=2, ensure_ascii=False)


def generated_dir(job_id: str) -> Path:
    d = config.GENERATED_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d
