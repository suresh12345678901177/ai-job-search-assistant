"""Free-form profile updates: the user describes new info in plain English
(a new project, a new skill, a new achievement) and this figures out where
it belongs and merges it in.

Same defensive pattern as tailor.tailor_resume: the LLM only proposes a
small, typed "update plan" (new skills, bullets to add to a *named existing*
company, new project entries, ...). The code applies that plan with
exact-match/dedup checks, so a weaker local model can't silently rewrite,
drop, or duplicate anything already in the profile - it can only append
genuinely new, explicitly-stated facts.
"""
import copy

from . import llm_client

UPDATE_SYSTEM = (
    "You extract new resume-relevant facts from a short note a candidate gives you, and turn "
    "them into a structured update. Only include information the candidate actually stated - "
    "never invent skills, projects, employers, metrics, or achievements beyond what's given. "
    "If something is ambiguous or not clearly stated, leave it out rather than guessing. "
    "Critically: if the note is a general instruction, request, opinion, or vague goal rather "
    "than a specific, concrete new fact (examples of NOT facts: 'make my resume better', "
    "'help me get hired faster', 'update everything') - it contains nothing to extract, so "
    "return every field empty/null. Never turn an instruction into a fake project or skill."
)


def build_update_plan(profile: dict, new_info: str) -> dict:
    experience_summary = [
        {"company": e.get("company", ""), "title": e.get("title", "")}
        for e in profile.get("experience", [])
    ]

    return llm_client.call_json(
        system=UPDATE_SYSTEM,
        user=(
            f"Candidate's existing roles (company/title only): {experience_summary}\n"
            f"Candidate's existing skills: {profile.get('skills', [])}\n"
            f"Candidate's existing project names: {[p.get('name', '') for p in profile.get('projects', [])]}\n\n"
            f"New information from the candidate:\n{new_info}\n\n"
            "Return ONLY this JSON shape:\n"
            "{\n"
            '  "summary_update": "a rewritten professional summary incorporating this new info if it changes '
            'the overall picture, or null if the summary should stay as-is",\n'
            '  "new_skills": ["skills explicitly mentioned that are not already in the existing skills list"],\n'
            '  "experience_updates": [{"company": "<must exactly match one of the existing companies above>", '
            '"add_bullets": ["new bullet(s) for that role"]}],\n'
            '  "new_projects": [{"name": "...", "description": "", "bullets": ["..."], "link": ""}],\n'
            '  "new_certifications": ["..."]\n'
            "}\n"
            "Use experience_updates only when the new info is clearly about ongoing work at one of the "
            "candidate's existing companies listed above. Use new_projects for anything separate/standalone "
            "(including work at a company not already listed, or personal/independent work). Leave any field "
            "as an empty list (or null for summary_update) if nothing applies."
        ),
        max_tokens=2000,
    )


def apply_update(profile: dict, plan: dict) -> tuple[dict, list[str]]:
    profile = copy.deepcopy(profile)
    changes: list[str] = []

    if plan.get("summary_update"):
        profile["summary"] = plan["summary_update"]
        changes.append("Rewrote summary to incorporate the new info")

    skills = profile.setdefault("skills", [])
    skills_lower = {s.lower() for s in skills}
    for skill in plan.get("new_skills") or []:
        skill = skill.strip() if isinstance(skill, str) else ""
        # a real skill name is a short noun phrase ("Docker", "Kubernetes") - anything this
        # long is almost certainly a misfired instruction/sentence, not an actual skill.
        if skill and len(skill.split()) <= 6 and skill.lower() not in skills_lower:
            skills.append(skill)
            skills_lower.add(skill.lower())
            changes.append(f"Added skill: {skill}")

    for update in plan.get("experience_updates") or []:
        company = (update.get("company") or "").strip().lower()
        if not company:
            continue
        for exp in profile.get("experience", []):
            if exp.get("company", "").strip().lower() == company:
                bullets = exp.setdefault("bullets", [])
                bullets_lower = {b.lower() for b in bullets}
                for bullet in update.get("add_bullets") or []:
                    if isinstance(bullet, str) and bullet.strip() and bullet.lower() not in bullets_lower:
                        bullets.append(bullet.strip())
                        bullets_lower.add(bullet.lower())
                        changes.append(f"Added bullet to {exp.get('company')}: {bullet.strip()}")
                break

    projects = profile.setdefault("projects", [])
    project_names_lower = {p.get("name", "").lower() for p in projects}
    for proj in plan.get("new_projects") or []:
        name = (proj.get("name") or "").strip()
        bullets = [b for b in (proj.get("bullets") or []) if isinstance(b, str) and b.strip()]
        description = (proj.get("description") or "").strip()
        # a real project name is a short title, not a full sentence/instruction, and a real
        # project has *some* substance behind it (a bullet or description) - reject anything
        # that's just a bare, long name with nothing else, which is a sign of a misfired note.
        looks_like_a_title = name and len(name.split()) <= 12
        has_substance = bool(bullets or description)
        if looks_like_a_title and has_substance and name.lower() not in project_names_lower:
            projects.append(
                {
                    "name": name,
                    "description": description,
                    "bullets": bullets,
                    "link": proj.get("link", "") or "",
                }
            )
            project_names_lower.add(name.lower())
            changes.append(f"Added project: {name}")

    certifications = profile.setdefault("certifications", [])
    certs_lower = {c.lower() for c in certifications}
    for cert in plan.get("new_certifications") or []:
        if isinstance(cert, str) and cert.strip() and cert.lower() not in certs_lower:
            certifications.append(cert.strip())
            certs_lower.add(cert.lower())
            changes.append(f"Added certification: {cert.strip()}")

    return profile, changes
