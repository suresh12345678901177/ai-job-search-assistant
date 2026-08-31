from . import claude_client, store


def suggest(profile: dict, target_role: str | None = None) -> dict:
    recent_jobs = store.list_jobs()[-5:]
    job_context = "\n".join(
        f"- {j.get('title', '')} at {j.get('company', '')}" for j in recent_jobs
    ) or "(no saved jobs yet)"

    role_hint = target_role or ", ".join(profile.get("target_roles") or []) or "(not specified)"

    return claude_client.call_json(
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
            '"linkedin_headline": "under 220 chars", '
            '"linkedin_about": "3-4 short paragraphs, first person", '
            '"linkedin_skills": ["ordered list of skills to pin, most important first"], '
            '"naukri_headline": "under 250 chars", '
            '"naukri_key_skills": ["comma-list-friendly skills for Naukri key skills field"]'
            "}"
        ),
        max_tokens=1500,
    )
