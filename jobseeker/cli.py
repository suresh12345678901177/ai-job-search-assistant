import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import (
    config,
    github_profile,
    job_alerts,
    polish,
    profile_suggest,
    profile_update,
    resume_parser,
    resume_writer,
    store,
    tailor,
    tracker,
)
from .browser import session as browser_session

console = Console()


@click.group()
def cli():
    """AI-assisted job search: tailor your resume, match jobs, draft applications,
    and semi-automate LinkedIn/Naukri (you always click the final submit)."""
    config.ensure_dirs()


@cli.command("ingest-resume")
@click.argument("path", type=click.Path(exists=True))
def ingest_resume(path: str):
    """Parse a PDF/DOCX resume into data/profile.json."""
    profile = resume_parser.ingest(Path(path))
    console.print(f"[green]Parsed resume for {profile.get('contact', {}).get('name', '(unknown name)')}[/]")
    console.print(f"Saved to {config.PROFILE_PATH}")
    console.print("Review it and fill in 'target_roles' - it helps tailoring and profile suggestions.")


@cli.command("polish-resume")
def polish_resume():
    """Get a general (job-agnostic) critique of your resume, then optionally apply improvements."""
    profile = store.load_profile()
    result = polish.critique(profile)
    console.print("[bold]Findings:[/]")
    for finding in result.get("findings", []):
        console.print(f"  - {finding}")

    if click.confirm("\nApply an improved rewrite (verbs/tightening/keywords, no invented facts)?"):
        improved = polish.improve(profile)
        improved["_raw_text"] = profile.get("_raw_text", "")
        store.save_profile(improved)
        console.print(f"[green]Updated {config.PROFILE_PATH}[/]")


@cli.command("update-info")
@click.option("--file", "info_file", type=click.Path(exists=True), help="Path to a text file with the new info.")
def update_info_cmd(info_file: str | None):
    """Give it any new info in plain English (a new project, skill, achievement) - it figures
    out where it belongs, merges it truthfully into your profile, and regenerates your resume
    and LinkedIn/Naukri suggestions automatically."""
    if info_file:
        new_info = Path(info_file).read_text(encoding="utf-8")
    else:
        console.print("Paste/type the new information, then press Ctrl+Z then Enter (Windows) to finish:")
        new_info = sys.stdin.read()
    new_info = new_info.strip()
    if not new_info:
        raise SystemExit("No information given.")

    profile = store.load_profile()
    console.print(f"Processing with the {config.LLM_BACKEND} backend...")
    plan = profile_update.build_update_plan(profile, new_info)
    updated_profile, changes = profile_update.apply_update(profile, plan)

    if not changes:
        console.print("[yellow]Nothing new detected to add - profile left unchanged.[/]")
        return

    store.save_profile(updated_profile)
    console.print("[green]Applied changes:[/]")
    for change in changes:
        console.print(f"  + {change}")

    master_dir = store.generated_dir("master")
    resume_writer.render_docx(updated_profile, master_dir / "resume.docx")
    resume_writer.render_txt(updated_profile, master_dir / "resume.txt")
    console.print(f"Regenerated master resume in {master_dir}")

    suggestions = profile_suggest.suggest(updated_profile)
    (config.DATA_DIR / "profile_suggestions.json").write_text(
        json.dumps(suggestions, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    console.print("Regenerated LinkedIn/Naukri suggestions -> data/profile_suggestions.json")
    console.print(
        "\nRun `update-profile --site linkedin` (or naukri) whenever you want to push these into your real profile."
    )


@cli.command("add-job")
@click.option("--title", required=True)
@click.option("--company", required=True)
@click.option("--url", required=True, help="The job posting URL (you'll apply here later).")
@click.option("--file", "jd_file", type=click.Path(exists=True), help="Path to a text file with the JD.")
def add_job(title: str, company: str, url: str, jd_file: str | None):
    """Save a job posting (paste the JD on stdin if --file is not given)."""
    if jd_file:
        description = Path(jd_file).read_text(encoding="utf-8")
    else:
        console.print("Paste the job description, then press Ctrl+Z then Enter (Windows) to finish:")
        description = sys.stdin.read()

    job_id = store.save_job(
        {"title": title, "company": company, "url": url, "description": description.strip()}
    )
    tracker.upsert(job_id, title, company, url, status="saved")
    console.print(f"[green]Saved job as '{job_id}'[/]")


@cli.command("jobs")
def list_jobs_cmd():
    """List saved jobs."""
    jobs = store.list_jobs()
    table = Table()
    for col in ("id", "title", "company", "saved_at"):
        table.add_column(col)
    for job in jobs:
        table.add_row(job["id"], job.get("title", ""), job.get("company", ""), job.get("saved_at", ""))
    console.print(table)


@cli.command("match")
@click.argument("job_id")
def match_cmd(job_id: str):
    """Score how well your resume fits a saved job."""
    profile = store.load_profile()
    job = store.load_job(job_id)
    result = tailor.score_match(profile, job)
    console.print(f"[bold]Fit score: {result.get('score')}/100[/]")
    console.print("[green]Strengths:[/]")
    for s in result.get("strengths", []):
        console.print(f"  + {s}")
    console.print("[yellow]Gaps:[/]")
    for g in result.get("gaps", []):
        console.print(f"  - {g}")
    console.print("[cyan]Keywords to emphasize:[/] " + ", ".join(result.get("keywords_to_emphasize", [])))


@cli.command("tailor")
@click.argument("job_id")
def tailor_cmd(job_id: str):
    """Generate a tailored resume + cover letter for a saved job."""
    profile = store.load_profile()
    job = store.load_job(job_id)

    console.print("Tailoring resume...")
    tailored_profile = tailor.tailor_resume(profile, job)
    console.print("Writing cover letter...")
    cover_letter = tailor.write_cover_letter(profile, job)

    out_dir = store.generated_dir(job_id)
    resume_writer.render_docx(tailored_profile, out_dir / "resume.docx")
    resume_writer.render_txt(tailored_profile, out_dir / "resume.txt")
    resume_writer.render_pdf(tailored_profile, out_dir / "resume.pdf")
    (out_dir / "cover_letter.txt").write_text(cover_letter, encoding="utf-8")
    (out_dir / "tailored_profile.json").write_text(
        json.dumps(tailored_profile, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    tracker.set_status(job_id, "tailored")
    console.print(f"[green]Wrote tailored materials to {out_dir}[/]")


@cli.command("suggest-profile")
@click.option("--target", default=None, help="Target role focus, e.g. 'senior backend engineer'.")
def suggest_profile_cmd(target: str | None):
    """Generate suggested LinkedIn/Naukri headline, About, and skills text."""
    profile = store.load_profile()
    suggestions = profile_suggest.suggest(profile, target)
    out_path = config.DATA_DIR / "profile_suggestions.json"
    out_path.write_text(json.dumps(suggestions, indent=2, ensure_ascii=False), encoding="utf-8")

    console.print("[bold]LinkedIn headline:[/] " + suggestions.get("linkedin_headline", ""))
    console.print("\n[bold]LinkedIn About:[/]\n" + suggestions.get("linkedin_about", ""))
    console.print("\n[bold]Naukri headline:[/] " + suggestions.get("naukri_headline", ""))
    console.print(f"\nFull suggestions saved to {out_path}")


@cli.command("login")
@click.argument("site", type=click.Choice(["linkedin", "naukri"]))
def login_cmd(site: str):
    """Open a browser to log in manually and save the session (no password is stored)."""
    browser_session.login(site)


@cli.command("apply")
@click.argument("job_id")
@click.option("--site", type=click.Choice(["linkedin", "naukri"]), required=True)
def apply_cmd(job_id: str, site: str):
    """Semi-auto fill an application: it stops before the final submit for you to review."""
    profile = store.load_profile()
    job = store.load_job(job_id)

    generated = store.generated_dir(job_id)
    resume_path = generated / "resume.docx"
    if not resume_path.exists():
        console.print("[yellow]No tailored resume found yet - run `tailor` first. Using master resume instead.[/]")
        resume_path = config.DATA_DIR / "resume_original.pdf"
        if not resume_path.exists():
            candidates = list(config.DATA_DIR.glob("resume_original.*"))
            if not candidates:
                raise SystemExit("No resume file available at all. Run `ingest-resume` first.")
            resume_path = candidates[0]

    with browser_session.open_session(site) as page:
        if site == "linkedin":
            from .browser import linkedin as site_module
        else:
            from .browser import naukri as site_module
        site_module.apply_to_job(page, job, profile, resume_path)
        input("\nPress Enter here once you're done in the browser (this closes the session)... ")

    tracker.set_status(job_id, "applied")
    console.print(f"[green]Marked '{job_id}' as applied in the tracker.[/]")


@cli.command("update-profile")
@click.option("--site", type=click.Choice(["linkedin", "naukri"]), required=True)
@click.option("--target", default=None, help="Target role focus for the suggestions.")
def update_profile_cmd(site: str, target: str | None):
    """Semi-auto open your profile editor with suggested text filled in (you click Save)."""
    profile = store.load_profile()
    suggestions = profile_suggest.suggest(profile, target)

    with browser_session.open_session(site) as page:
        if site == "linkedin":
            from .browser import profile_linkedin

            profile_linkedin.update_intro_and_about(page, suggestions)
            profile_linkedin.set_open_to_work(page, profile)
        else:
            from .browser import profile_naukri

            profile_naukri.update_headline_and_skills(page, suggestions)
        input("\nPress Enter here once you're done reviewing/saving in the browser... ")


@cli.command("check-job-alerts")
@click.option("--loop", type=int, default=0, help="Seconds between checks. Omit to check once and exit.")
def check_job_alerts_cmd(loop: int):
    """Check your email's job-alert folder for new postings (LinkedIn's/Naukri's
    own alert emails - not scraping), save + score any real postings found.
    Requires EMAIL_ADDRESS and EMAIL_APP_PASSWORD in .env. Safe to run
    unattended: only reads email and writes to your local job store."""
    import time

    profile = store.load_profile()
    while True:
        console.print(f"Checking '{job_alerts.FOLDER}' folder for new alerts...")
        found = job_alerts.check_inbox(profile)
        if found:
            table = Table()
            for col in ("job_id", "title", "company", "score"):
                table.add_column(col)
            for job in found:
                table.add_row(job["job_id"], job["title"], job["company"], str(job["score"]))
            console.print(table)
            console.print(f"[green]{len(found)} new posting(s) saved.[/] Run `match`/`tailor` on any of them.")
        else:
            console.print("No new relevant postings.")

        if loop <= 0:
            break
        console.print(f"Sleeping {loop}s before next check...")
        time.sleep(loop)


@cli.command("update-github-profile")
def update_github_profile_cmd():
    """Sync your GitHub profile README and bio from profile.json. Safe to run
    unattended - your own account, via GitHub's own API, fully reversible."""
    profile = store.load_profile()
    try:
        result = github_profile.update_github_profile(profile)
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc))

    if result["created_repo"]:
        console.print(f"[green]Created profile repo '{result['username']}/{result['username']}'[/]")
    console.print("[green]README updated[/]" if result["readme_updated"] else "README already up to date")
    console.print("[green]Bio updated[/]" if result["bio_updated"] else "Bio not updated")
    console.print(f"https://github.com/{result['username']}")


@cli.command("debug-profile")
@click.option("--site", type=click.Choice(["linkedin", "naukri"]), required=True)
def debug_profile_cmd(site: str):
    """Screenshot your real profile page and dump button labels - use this when
    update-profile stops finding a field/button after a site redesign, to read
    off the real selectors instead of guessing."""
    with browser_session.open_session(site) as page:
        from .browser import diagnostics

        if site == "linkedin":
            screenshot, buttons = diagnostics.dump_linkedin_profile(page)
        else:
            screenshot, buttons = diagnostics.dump_naukri_profile(page)
        console.print(f"[green]Screenshot:[/] {screenshot}")
        console.print(f"[green]Button dump:[/] {buttons}")


@cli.group("track")
def track_group():
    """View or update your application tracker."""


@track_group.command("list")
def track_list():
    rows = tracker.list_all()
    table = Table()
    for col in ("job_id", "title", "company", "status", "updated_at"):
        table.add_column(col)
    for row in rows:
        table.add_row(row["job_id"], row["title"], row["company"], row["status"], row["updated_at"])
    console.print(table)


@track_group.command("set-status")
@click.argument("job_id")
@click.argument("status", type=click.Choice(tracker.STATUSES))
def track_set_status(job_id: str, status: str):
    tracker.set_status(job_id, status)
    console.print(f"[green]{job_id} -> {status}[/]")


@cli.command("webapp")
@click.option("--port", default=5000, help="Port to serve the dashboard on.")
def webapp_cmd(port: int):
    """Launch the local web dashboard (profile, matched jobs, tailoring, tracker)."""
    from . import webapp

    console.print(f"[green]Dashboard running at http://127.0.0.1:{port} - open it in your browser.[/]")
    console.print("[dim]Press Ctrl+C here to stop it.[/]")
    webapp.run(port=port)


if __name__ == "__main__":
    cli()
