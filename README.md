# Job Search Assistant

A local, RAG-powered assistant that helps you: parse and improve your resume,
match and tailor it to specific jobs, draft cover letters and application
answers, semi-automate filling LinkedIn/Naukri applications and profile
edits, and track everything.

## Risk & ethics (read this first)

LinkedIn's and Naukri's Terms of Service prohibit automated
submission/scraping, and both run bot detection that can suspend accounts.
This tool is built **semi-automatic on purpose**:

- It never stores your password. `login` opens a real browser window for
  you to log in manually (2FA/captcha included); only the resulting session
  cookies are saved locally to reuse the login.
- `apply` fills in what it confidently can (contact fields, resume upload,
  drafted answers to free-text questions) but **always stops before the
  final Submit/Send** so you review and click it yourself.
- Decision fields with real consequences (work authorization, sponsorship,
  salary, notice period) are deliberately left for you to answer, not
  guessed at.
- `update-profile` works the same way for LinkedIn/Naukri profile edits -
  it opens the editor and fills suggested text, you click Save.
- Selectors for these sites' DOM will break as the sites change their
  markup - when that happens the script logs what it couldn't do and falls
  back to manual, rather than failing silently.
- Use it at a human pace. Don't spam applications. There's no guarantee of
  outcomes - this speeds up the mechanical parts, it doesn't replace
  judgment about which jobs to actually pursue.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
# then edit .env and set ANTHROPIC_API_KEY
```

## Walkthrough

```powershell
# 1. Parse your resume into data/profile.json (the master, hand-editable source of truth)
python -m jobseeker.cli ingest-resume "C:\path\to\your_resume.pdf"

# 2. Optional: general resume critique + improvement pass (no specific job)
python -m jobseeker.cli polish-resume

# 3. Save a job you found by browsing normally
python -m jobseeker.cli add-job --title "Backend Engineer" --company "Acme" --url "https://..." --file jd.txt

# 4. See how well you match, and what's missing
python -m jobseeker.cli match <job_id>

# 5. Generate a tailored resume + cover letter for that job
python -m jobseeker.cli tailor <job_id>
# -> data/generated/<job_id>/resume.docx, resume.txt, cover_letter.txt

# 6. Suggested LinkedIn/Naukri headline, About, and skills text
python -m jobseeker.cli suggest-profile --target "backend engineer"

# 7. One-time manual login per site (opens a real browser window)
python -m jobseeker.cli login linkedin
python -m jobseeker.cli login naukri

# 8. Semi-auto fill an application - review and click Submit yourself
python -m jobseeker.cli apply <job_id> --site linkedin

# 9. Semi-auto fill profile edits - review and click Save yourself
python -m jobseeker.cli update-profile --site linkedin

# 10. Track everything
python -m jobseeker.cli track list
python -m jobseeker.cli track set-status <job_id> interviewing
```

Run `python -m jobseeker.cli --help` (or `<command> --help`) any time.

## How the RAG part works

Every resume bullet/project, every saved job description, and every
application answer you finalize becomes a retrievable document (see
`jobseeker/retrieval.py`). Retrieval uses TF-IDF + cosine similarity, not a
neural embedding model - it needs no extra API key or heavy install, and
fits a domain (resume/ATS keyword matching) that's substantially
keyword-driven anyway. Three places use it:

- **Matching/tailoring**: pulls your most relevant resume bullets for a
  given job description to ground scoring, resume rewriting, and cover
  letters.
- **Application answers**: pulls similar past questions/answers from
  `data/qa_bank.json` so free-text answers stay consistent in voice as you
  apply to more jobs - the bank grows every time you apply.

Everything the AI generates is explicitly constrained to rephrase/reorder
your real background, never to invent employers, titles, dates, or skills.

## Tests

```powershell
pytest
```

Covers the pure-Python pieces (retrieval ranking, resume rendering, job/
profile/tracker storage) that don't need the Claude API or a browser.
