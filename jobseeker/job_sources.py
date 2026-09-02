"""Aggregates real job postings from free, no-auth job-search APIs (not scraping -
these are public JSON APIs the sites themselves provide for this purpose).
"""
import json
import re
import urllib.error
import urllib.request

REMOTEOK_URL = "https://remoteok.com/api"
ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


def _fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _keywords(profile: dict) -> list[str]:
    keywords = [r.lower() for r in profile.get("target_roles", [])]
    keywords += [s.lower() for s in profile.get("skills", [])[:12]]
    return keywords


def _is_relevant(title: str, description: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    text = f"{title}\n{description}".lower()
    return any(kw in text for kw in keywords)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def fetch_remoteok(keywords: list[str]) -> list[dict]:
    try:
        items = _fetch_json(REMOTEOK_URL)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []

    jobs = []
    for item in items:
        if not isinstance(item, dict) or "id" not in item:
            continue  # first element is metadata, not a job
        title = item.get("position", "")
        description = _strip_html(item.get("description", ""))
        if not _is_relevant(title, description, keywords):
            continue
        jobs.append(
            {
                "title": title,
                "company": item.get("company", ""),
                "location": item.get("location", "Remote"),
                "url": item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id')}",
                "description": description,
                "source": "RemoteOK",
            }
        )
    return jobs


def fetch_arbeitnow(keywords: list[str]) -> list[dict]:
    try:
        items = _fetch_json(ARBEITNOW_URL).get("data", [])
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []

    jobs = []
    for item in items:
        title = item.get("title", "")
        description = _strip_html(item.get("description", ""))
        if not _is_relevant(title, description, keywords):
            continue
        jobs.append(
            {
                "title": title,
                "company": item.get("company_name", ""),
                "location": item.get("location") or ("Remote" if item.get("remote") else ""),
                "url": item.get("url", ""),
                "description": description,
                "source": "Arbeitnow",
            }
        )
    return jobs


def fetch_all(profile: dict) -> list[dict]:
    keywords = _keywords(profile)
    jobs = fetch_remoteok(keywords) + fetch_arbeitnow(keywords)
    seen_urls = set()
    deduped = []
    for job in jobs:
        if job["url"] and job["url"] not in seen_urls:
            seen_urls.add(job["url"])
            deduped.append(job)
    return deduped
