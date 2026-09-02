"""Discovers new job postings via LinkedIn's/Naukri's own job-alert emails -
the official, ToS-compliant mechanism both platforms provide for "notify me
the moment a matching job posts" - instead of scraping search pages, which
both platforms' Terms of Service prohibit.

Safe to run fully unattended: this only reads email and writes to your local
job store (data/jobs/, the sqlite tracker) - nothing is sent anywhere, and no
application is submitted. You still run `match`/`tailor`/`apply` yourself for
anything it finds.
"""
import email
import imaplib
import os
import re
from datetime import datetime, timezone
from email.header import decode_header

from . import config, llm_client, store, tailor

IMAP_SERVER = os.environ.get("JOB_ALERTS_IMAP_SERVER", "imap.gmail.com")
FOLDER = os.environ.get("JOB_ALERTS_FOLDER", "Job Alerts")
SEEN_LOG = config.DATA_DIR / "seen_job_alerts.txt"


def _load_seen() -> set[str]:
    if not SEEN_LOG.exists():
        return set()
    return set(line.strip() for line in SEEN_LOG.read_text(encoding="utf-8").splitlines() if line.strip())


def _mark_seen(message_id: str) -> None:
    config.ensure_dirs()
    with open(SEEN_LOG, "a", encoding="utf-8") as f:
        f.write(message_id + "\n")


def _decode_str(value) -> str:
    if not value:
        return ""
    decoded, enc = decode_header(value)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(enc or "utf-8", errors="ignore")
    return decoded


_HREF_RE = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
_URL_RE = re.compile(r'https?://[^\s()<>\[\]"\']+')


def _html_to_text_with_links(html: str) -> str:
    """Inlines each link's URL next to its text (e.g. 'View job (https://...)')
    before stripping tags, so a real apply URL survives into the plain text
    used for chunking/extraction below - the plain-text alternative most
    alert emails send often omits links entirely."""
    def _replace(m):
        url, text = m.group(1), re.sub("<[^<]+?>", " ", m.group(2)).strip()
        return f"{text} ({url})" if text else f"({url})"

    return re.sub("<[^<]+?>", " ", _HREF_RE.sub(_replace, html))


def _get_body(msg) -> str:
    if msg.is_multipart():
        html_part = text_part = None
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/html" and html_part is None:
                html_part = part.get_payload(decode=True).decode(errors="ignore")
            elif ctype == "text/plain" and text_part is None:
                text_part = part.get_payload(decode=True).decode(errors="ignore")
        if html_part:
            return _html_to_text_with_links(html_part)
        return text_part or ""
    payload = msg.get_payload(decode=True)
    return payload.decode(errors="ignore") if payload else ""


def _extract_job_url(chunk: str) -> str:
    """Picks the real apply/view-job URL out of an email chunk - preferring an
    actual LinkedIn/Naukri job link over any tracking/unsubscribe/social link
    that might also appear in the same block."""
    urls = [u.rstrip(").,;'\"") for u in _URL_RE.findall(chunk)]
    for url in urls:
        if "linkedin.com/jobs" in url or "naukri.com" in url:
            return url
    return urls[0] if urls else ""


def _relevance_keywords(profile: dict) -> list[str]:
    """Derived from the user's own target roles/skills rather than a fixed
    list, so this works for whatever field the user is actually in."""
    keywords = set()
    for role in profile.get("target_roles") or []:
        keywords.add(role.lower())
    for skill in (profile.get("skills") or [])[:10]:
        keywords.add(skill.lower())
    return list(keywords)


def _is_relevant(subject: str, body: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    text = f"{subject} {body}".lower()
    return any(kw in text for kw in keywords)


def _split_candidate_postings(body: str) -> list[str]:
    """Job alert emails often bundle multiple postings in one email. This is
    a best-effort split on blank-line runs - not perfect for every alert
    format, but the LLM structuring step below discards anything that isn't
    actually a job posting, so a noisy split is safe, just wasteful."""
    chunks = re.split(r"\n\s*\n\s*\n+", body)
    return [c.strip() for c in chunks if len(c.strip()) > 200]


def structure_posting(raw_text: str) -> dict | None:
    """Ask the LLM to pull a clean title/company/description out of a raw
    email chunk, or say it's not actually a job posting (a footer, an ad,
    unsubscribe text, etc)."""
    result = llm_client.call_json(
        system=(
            "You extract a single job posting's title, company, and full description from a "
            "raw chunk of a job-alert email. If this chunk is NOT actually a job posting - it's "
            "a footer, an ad, unsubscribe text, or unrelated content - return "
            '{"is_job_posting": false}.'
        ),
        user=f"Raw email chunk:\n{raw_text}",
        max_tokens=1500,
    )
    if not result or not result.get("is_job_posting", True) or not result.get("title"):
        return None
    return {
        "title": result.get("title", "").strip(),
        "company": result.get("company", "").strip(),
        "description": result.get("description", raw_text).strip(),
    }


def check_inbox(profile: dict) -> list[dict]:
    """Connects via IMAP, finds unread messages in the job-alerts folder,
    extracts and structures any real postings, saves them to the local job
    store, and scores each against the profile. Returns a summary per job
    found. Requires EMAIL_ADDRESS and EMAIL_APP_PASSWORD in .env."""
    address = os.environ.get("EMAIL_ADDRESS")
    app_password = os.environ.get("EMAIL_APP_PASSWORD")
    if not address or not app_password:
        raise SystemExit(
            "Set EMAIL_ADDRESS and EMAIL_APP_PASSWORD in .env first (use a Gmail App Password, "
            "never your real password: Google Account > Security > App Passwords)."
        )

    seen = _load_seen()
    keywords = _relevance_keywords(profile)
    found: list[dict] = []

    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    try:
        mail.login(address, app_password)
        mail.select(f'"{FOLDER}"')

        status, data = mail.search(None, "UNSEEN")
        ids = data[0].split() if data and data[0] else []

        for msg_id in ids:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            message_id = _decode_str(msg.get("Message-ID")) or str(msg_id)

            if message_id in seen:
                continue

            subject = _decode_str(msg.get("Subject"))
            body = _get_body(msg)

            if not _is_relevant(subject, body, keywords):
                _mark_seen(message_id)
                continue

            for chunk in _split_candidate_postings(body):
                posting = structure_posting(chunk)
                if not posting or not posting["title"]:
                    continue

                job_id = store.save_job(
                    {
                        "title": posting["title"],
                        "company": posting["company"] or "(unknown - from email alert)",
                        "url": _extract_job_url(chunk),
                        "description": posting["description"],
                        "source": "email_alert",
                    }
                )
                match = tailor.score_match(profile, store.load_job(job_id))
                found.append(
                    {
                        "job_id": job_id,
                        "title": posting["title"],
                        "company": posting["company"],
                        "score": match.get("score"),
                    }
                )

            _mark_seen(message_id)
    finally:
        try:
            mail.logout()
        except Exception:
            pass

    return found
