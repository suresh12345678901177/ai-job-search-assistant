from . import llm_client, store


def suggest(profile: dict, target_role: str | None = None) -> dict:
    recent_jobs = store.list_jobs()[-5:]
    job_context = "\n".join(
        f"- {j.get('title', '')} at {j.get('company', '')}" for j in recent_jobs
    ) or "(no saved jobs yet)"

    role_hint = target_role or ", ".join(profile.get("target_roles") or []) or "(not specified)"

    raw = llm_client.call_json(
        system=(
            "You write LinkedIn and Naukri profile copy that is specific and keyword-rich for "
            "recruiter search, grounded only in the candidate's real background - never invent "
            "employers, titles, or skills."
        ),
        user=(
            f"Target role focus: {role_hint}\n"
            f"Recently saved jobs (signal for what recruiters/roles to target):\n{job_context}\n\n"
            f"Candidate summary: {profile.get('summary', '')}\n"
            f"Candidate skills: {', '.join(profile.get('skills', []))}\n"
            f"Candidate experience: {[(e.get('title'), e.get('company')) for e in profile.get('experience', [])]}\n\n"
            "Return JSON: {"
            '"linkedin_headline": "under 220 chars, a single string", '
            '"linkedin_about": "3-4 short paragraphs joined into ONE string separated by blank lines, '
            'not a list", '
            '"linkedin_skills": ["ordered list of skills to pin, most important first"], '
            '"naukri_headline": "under 250 chars, a single string", '
            '"naukri_key_skills": ["a list of individual skill strings, not one comma-joined string"]'
            "}"
        ),
        max_tokens=1500,
    )
    return _normalize_suggestions(raw)


def _as_text(value, joiner: str = "\n\n") -> str:
    if isinstance(value, list):
        return joiner.join(str(v) for v in value)
    return str(value) if value else ""


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    return []


def _normalize_suggestions(raw: dict) -> dict:
    """A local model won't always follow the exact requested shape (e.g. returning
    a list where a string was asked for, or vice versa) - normalize so callers can
    rely on consistent types regardless of which LLM backend produced this."""
    return {
        "linkedin_headline": _as_text(raw.get("linkedin_headline"), joiner=" "),
        "linkedin_about": _as_text(raw.get("linkedin_about")),
        "linkedin_skills": _as_list(raw.get("linkedin_skills")),
        "naukri_headline": _as_text(raw.get("naukri_headline"), joiner=" "),
        "naukri_key_skills": _as_list(raw.get("naukri_key_skills")),
    }
