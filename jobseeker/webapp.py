"""Local dashboard: view your profile/resume, browse matched jobs pulled from
free job-search APIs and your email alerts, tailor + track applications, and
launch the existing semi-auto browser flows (which still stop before Submit).
Runs only on localhost - this is a personal tool, not a public service.
"""
import subprocess
import sys
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

from . import config, github_profile, job_alerts, job_sources, resume_writer, retrieval, store, tailor, tracker

REPO_ROOT = Path(__file__).resolve().parent.parent

app = Flask(__name__)
app.secret_key = "jobseeker-local-dashboard"


def _tracker_status_map() -> dict[str, str]:
    return {row["job_id"]: row["status"] for row in tracker.list_all()}


def _quick_match_score(profile: dict, description: str) -> int:
    if not description:
        return 0
    matches = retrieval.top_resume_matches(profile, description, top_k=5)
    if not matches:
        return 0
    avg = sum(score for _, score in matches) / len(matches)
    return max(0, min(100, round(avg * 220)))


@app.route("/")
def dashboard():
    profile = store.load_profile()
    jobs = store.list_jobs()
    statuses = _tracker_status_map()
    stats = {
        "total_jobs": len(jobs),
        "tailored": sum(1 for s in statuses.values() if s in ("tailored", "applied", "interviewing", "offer")),
        "applied": sum(1 for s in statuses.values() if s in ("applied", "interviewing", "offer")),
        "interviewing": sum(1 for s in statuses.values() if s in ("interviewing", "offer")),
        "offers": sum(1 for s in statuses.values() if s == "offer"),
    }
    recent = sorted(tracker.list_all(), key=lambda r: r["updated_at"], reverse=True)[:6]
    return render_template("dashboard.html", profile=profile, stats=stats, recent=recent, active="dashboard")


@app.route("/profile")
def profile_view():
    profile = store.load_profile()
    return render_template("profile.html", profile=profile, active="profile")


@app.route("/jobs")
def jobs_view():
    profile = store.load_profile()
    jobs = store.list_jobs()
    statuses = _tracker_status_map()
    for job in jobs:
        job["status"] = statuses.get(job["id"], "saved")
        job["keyword_score"] = _quick_match_score(profile, job.get("description", ""))
        ai_score = job.get("match", {}).get("score") if isinstance(job.get("match"), dict) else None
        job["ai_score"] = ai_score
        job["sort_score"] = ai_score if ai_score is not None else job["keyword_score"]
    jobs.sort(key=lambda j: j["sort_score"], reverse=True)

    q = request.args.get("q", "").strip().lower()
    if q:
        jobs = [j for j in jobs if q in j.get("title", "").lower() or q in j.get("company", "").lower()]

    return render_template("jobs.html", jobs=jobs, q=q, active="jobs")


@app.route("/jobs/score-batch", methods=["POST"])
def jobs_score_batch():
    profile = store.load_profile()
    jobs = store.list_jobs()
    for job in jobs:
        job["keyword_score"] = _quick_match_score(profile, job.get("description", ""))
    unscored = [j for j in jobs if not isinstance(j.get("match"), dict)]
    unscored.sort(key=lambda j: j["keyword_score"], reverse=True)

    limit = 8
    scored = 0
    for job in unscored[:limit]:
        try:
            job["match"] = tailor.score_match(profile, job)
            store.save_job(job)
            scored += 1
        except Exception:
            continue

    flash(f"AI-scored {scored} of your top keyword-matched jobs (capped at {limit} per run to keep this from taking forever on a local model).")
    return redirect(url_for("jobs_view"))


@app.route("/jobs/fetch", methods=["POST"])
def jobs_fetch():
    profile = store.load_profile()
    fetched = job_sources.fetch_all(profile)
    existing_urls = {j.get("url") for j in store.list_jobs()}
    added = 0
    for job in fetched:
        if not job.get("url") or job["url"] in existing_urls:
            continue
        job_id = store.save_job(job)
        tracker.upsert(job_id, job["title"], job["company"], job["url"], "saved")
        added += 1
    flash(f"Fetched {len(fetched)} matching postings from RemoteOK/Arbeitnow, added {added} new.")
    return redirect(url_for("jobs_view"))


@app.route("/jobs/<job_id>")
def job_detail(job_id):
    profile = store.load_profile()
    job = store.load_job(job_id)
    statuses = _tracker_status_map()
    job["status"] = statuses.get(job_id, "saved")

    matches = retrieval.top_resume_matches(profile, job.get("description", ""), top_k=8)
    match_bullets = [
        {"text": doc.text, "tag": doc.meta.get("header") or doc.meta.get("name") or doc.doc_type}
        for doc, _ in matches
    ]

    gen_dir = store.generated_dir(job_id)
    generated = {
        "resume_docx": (gen_dir / "resume.docx").exists(),
        "resume_pdf": (gen_dir / "resume.pdf").exists(),
        "cover_letter": (gen_dir / "cover_letter.txt").exists(),
    }
    url_lower = job.get("url", "").lower()
    is_linkedin = "linkedin.com" in url_lower
    is_naukri = "naukri.com" in url_lower

    return render_template(
        "job_detail.html",
        job=job,
        match_bullets=match_bullets,
        generated=generated,
        statuses=tracker.STATUSES,
        is_linkedin=is_linkedin,
        is_naukri=is_naukri,
        active="jobs",
    )


@app.route("/jobs/<job_id>/tailor", methods=["POST"])
def job_tailor(job_id):
    profile = store.load_profile()
    job = store.load_job(job_id)
    try:
        tailored = tailor.tailor_resume(profile, job)
        cover_letter = tailor.write_cover_letter(profile, job)

        out_dir = store.generated_dir(job_id)
        resume_writer.render_docx(tailored, out_dir / "resume.docx")
        resume_writer.render_txt(tailored, out_dir / "resume.txt")
        resume_writer.render_pdf(tailored, out_dir / "resume.pdf")
        (out_dir / "cover_letter.txt").write_text(cover_letter, encoding="utf-8")

        tracker.upsert(job_id, job.get("title", ""), job.get("company", ""), job.get("url", ""), "saved")
        tracker.set_status(job_id, "tailored")
        flash("Tailored resume and cover letter generated below.")
    except Exception as exc:
        flash(f"Tailoring failed: {exc}")
    return redirect(url_for("job_detail", job_id=job_id))


@app.route("/jobs/<job_id>/score", methods=["POST"])
def job_score(job_id):
    profile = store.load_profile()
    job = store.load_job(job_id)
    try:
        result = tailor.score_match(profile, job)
        job["match"] = result
        store.save_job(job)
        flash(f"AI match score: {result.get('score', '?')}/100")
    except Exception as exc:
        flash(f"Scoring failed: {exc}")
    return redirect(url_for("job_detail", job_id=job_id))


@app.route("/jobs/<job_id>/status", methods=["POST"])
def job_status(job_id):
    new_status = request.form["status"]
    job = store.load_job(job_id)
    tracker.upsert(job_id, job.get("title", ""), job.get("company", ""), job.get("url", ""), new_status)
    tracker.set_status(job_id, new_status)
    return redirect(url_for("job_detail", job_id=job_id))


@app.route("/jobs/<job_id>/apply", methods=["POST"])
def job_apply(job_id):
    site = request.form.get("site")
    if site in ("linkedin", "naukri"):
        popen_kwargs = {"cwd": str(REPO_ROOT)}
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        subprocess.Popen(
            [sys.executable, "-m", "jobseeker.cli", "apply", job_id, "--site", site],
            **popen_kwargs,
        )
        flash(
            f"Opening a browser window to semi-auto fill this application on "
            f"{site.title()} - review everything and click Submit yourself there."
        )
    return redirect(url_for("job_detail", job_id=job_id))


@app.route("/tracker")
def tracker_view():
    apps = tracker.list_all()
    board = {status: [a for a in apps if a["status"] == status] for status in tracker.STATUSES}
    return render_template("tracker.html", board=board, statuses=tracker.STATUSES, active="tracker")


@app.route("/sync/github", methods=["POST"])
def sync_github():
    profile = store.load_profile()
    try:
        result = github_profile.update_github_profile(profile)
        flash(f"GitHub synced - bio updated: {result.get('bio_updated')}, README updated: {result.get('readme_updated')}")
    except Exception as exc:
        flash(f"GitHub sync failed: {exc}")
    return redirect(url_for("dashboard"))


@app.route("/sync/email-alerts", methods=["POST"])
def sync_email_alerts():
    profile = store.load_profile()
    try:
        found = job_alerts.check_inbox(profile)
        flash(f"Checked email job alerts - {len(found)} new postings found.")
    except Exception as exc:
        flash(f"Email alert check failed: {exc} (set EMAIL_ADDRESS/EMAIL_APP_PASSWORD in .env)")
    return redirect(url_for("dashboard"))


@app.route("/download/<job_id>/<path:filename>")
def download(job_id, filename):
    path = store.generated_dir(job_id) / filename
    if not path.exists():
        return "Not found", 404
    return send_file(path, as_attachment=True)


def run(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    config.ensure_dirs()
    app.run(host=host, port=port, debug=debug, threaded=True)
