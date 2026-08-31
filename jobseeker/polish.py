from . import claude_client

POLISH_SYSTEM = (
    "You are a senior resume reviewer. You improve resumes without inventing new facts: "
    "strengthen weak verbs, add quantification only where the source text already implies a "
    "number or scale (never fabricate metrics), tighten wording, and improve ATS keyword "
    "coverage for the candidate's stated target roles. You may not add employers, titles, "
    "dates, or skills that are not already present."
)


def critique(profile: dict) -> dict:
    return claude_client.call_json(
        system=POLISH_SYSTEM,
        user=(
            f"Target roles: {profile.get('target_roles') or '(not specified)'}\n\n"
            f"Full profile JSON:\n{profile}\n\n"
            "Return JSON: {\"findings\": [\"specific, actionable critique\", ...]} "
            "covering weak verbs, missing quantification, vague bullets, ATS keyword gaps, "
            "and consistency issues (verb tense, formatting of dates, etc)."
        ),
        max_tokens=2048,
    )


def improve(profile: dict) -> dict:
    return claude_client.call_json(
        system=POLISH_SYSTEM,
        user=(
            f"Target roles: {profile.get('target_roles') or '(not specified)'}\n\n"
            f"Full profile JSON:\n{profile}\n\n"
            "Rewrite this into an improved version of the exact same JSON schema: stronger "
            "action verbs, tighter bullets, consistent tense (past roles in past tense, "
            "current role in present tense), better ATS keyword coverage for the target roles. "
            "Do not add facts not already present. Return the full profile JSON."
        ),
        max_tokens=4096,
    )
