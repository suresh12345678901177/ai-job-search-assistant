from . import claude_client, retrieval

TRUTHFULNESS_RULE = (
    "Hard rule: you may rephrase, reorder, and emphasize only content that is present "
    "in the candidate's real background below. Never invent employers, titles, dates, "
    "skills, tools, or achievements that are not grounded in the provided material."
)


def score_match(profile: dict, job: dict) -> dict:
    matches = retrieval.top_resume_matches(profile, job["description"], top_k=12)
    context = retrieval.format_matches_for_prompt(matches)

    return claude_client.call_json(
        system=(
            "You are a career coach scoring how well a candidate's real background fits a "
            "job description. Be honest and specific - do not inflate the score to be "
            "encouraging. " + TRUTHFULNESS_RULE
        ),
        user=(
            f"JOB TITLE: {job.get('title', '')}\nCOMPANY: {job.get('company', '')}\n\n"
            f"JOB DESCRIPTION:\n{job['description']}\n\n"
            f"MOST RELEVANT CANDIDATE BACKGROUND (retrieved):\n{context}\n\n"
            f"CANDIDATE SUMMARY: {profile.get('summary', '')}\n"
            f"CANDIDATE SKILLS: {', '.join(profile.get('skills', []))}\n\n"
            "Return JSON: {\"score\": 0-100, \"strengths\": [\"...\"], \"gaps\": [\"...\"], "
            "\"keywords_to_emphasize\": [\"...\"]}"
        ),
        max_tokens=2048,
    )


def tailor_resume(profile: dict, job: dict) -> dict:
    matches = retrieval.top_resume_matches(profile, job["description"], top_k=15)
    context = retrieval.format_matches_for_prompt(matches)

    return claude_client.call_json(
        system=(
            "You are an expert resume writer. You tailor a candidate's existing resume to a "
            "specific job by reordering and rewriting for relevance and ATS keyword alignment. "
            + TRUTHFULNESS_RULE
            + " Keep the exact same JSON schema as the input profile."
        ),
        user=(
            f"JOB TITLE: {job.get('title', '')}\nCOMPANY: {job.get('company', '')}\n\n"
            f"JOB DESCRIPTION:\n{job['description']}\n\n"
            f"MOST RELEVANT CANDIDATE BACKGROUND (retrieved via search, use as emphasis guide):\n{context}\n\n"
            f"FULL CANDIDATE PROFILE (ground truth, do not add facts beyond this):\n{profile}\n\n"
            "Produce a tailored version of this exact JSON profile: rewrite the summary to "
            "target this role, reorder skills to put the most relevant first, reorder each "
            "experience's bullets to lead with the most relevant ones and lightly rephrase them "
            "to mirror the job description's language/keywords where truthful. Keep companies, "
            "titles, dates, and education unchanged. Return the full profile JSON with the same "
            "top-level keys as the input."
        ),
        max_tokens=4096,
    )


def write_cover_letter(profile: dict, job: dict) -> str:
    matches = retrieval.top_resume_matches(profile, job["description"], top_k=10)
    context = retrieval.format_matches_for_prompt(matches)

    return claude_client.call(
        system=(
            "You write concise, specific, non-generic cover letters (3-4 short paragraphs, "
            "no cliches like 'I am excited to apply'). " + TRUTHFULNESS_RULE
        ),
        user=(
            f"Candidate name: {profile.get('contact', {}).get('name', '')}\n"
            f"Job title: {job.get('title', '')}\nCompany: {job.get('company', '')}\n\n"
            f"Job description:\n{job['description']}\n\n"
            f"Most relevant candidate background:\n{context}\n\n"
            "Write the cover letter body only (no address block, no salutation boilerplate "
            "beyond 'Dear Hiring Manager,' and a closing line with the candidate's name)."
        ),
        max_tokens=1200,
        temperature=0.6,
    )


def draft_answer(question: str, profile: dict, job: dict) -> str:
    resume_matches = retrieval.top_resume_matches(profile, f"{question}\n{job['description']}", top_k=6)
    resume_context = retrieval.format_matches_for_prompt(resume_matches)
    qa_matches = retrieval.top_qa_matches(question, top_k=3)
    qa_context = "\n".join(
        f"- Q: {m['question']}\n  A: {m['answer']}" for m in qa_matches
    ) or "(no similar past answers yet)"

    return claude_client.call(
        system=(
            "You draft honest, specific answers to job application questions in the "
            "candidate's voice, consistent with how they've answered similar questions before. "
            + TRUTHFULNESS_RULE
        ),
        user=(
            f"Application question: {question}\n\n"
            f"Job title: {job.get('title', '')} at {job.get('company', '')}\n\n"
            f"Relevant candidate background:\n{resume_context}\n\n"
            f"Similar past answers this candidate has given (for voice/consistency):\n{qa_context}\n\n"
            "Draft a concise answer (2-5 sentences unless the question clearly needs more)."
        ),
        max_tokens=600,
        temperature=0.5,
    )
