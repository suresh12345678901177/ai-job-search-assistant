"""Keeps your GitHub profile README and bio in sync with profile.json.

This is fully safe to automate unattended: it's your own GitHub account,
GitHub's API/CLI is explicitly built for scripted repo management (unlike
LinkedIn/Naukri), and every change is a normal git commit you can revert.

Uses the GitHub CLI (`gh`, already authenticated earlier in this project)
rather than asking for a separate personal access token.
"""
import shutil
import subprocess
from pathlib import Path

from . import config

GIT_EXE = str(Path.home() / "AppData/Local/Programs/Git/cmd/git.exe")
GH_EXE = r"C:\Program Files\GitHub CLI\gh.exe"


def _resolve_exe(name: str, known_path: str) -> str:
    return known_path if Path(known_path).exists() else (shutil.which(name) or name)


def _run(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd)


def extract_github_username(profile: dict) -> str | None:
    for link in profile.get("contact", {}).get("other_links", []):
        if "github.com/" in link:
            parts = link.rstrip("/").split("github.com/")[-1].split("/")
            if parts and parts[0]:
                return parts[0]
    return None


def build_readme(profile: dict) -> str:
    contact = profile.get("contact", {})
    lines = [f"### Hi, I'm {contact.get('name', '').strip() or 'there'}", "", profile.get("summary", ""), ""]

    target_roles = profile.get("target_roles") or []
    if target_roles:
        lines += [f"**Looking for:** {', '.join(target_roles)}", ""]

    if profile.get("skills"):
        lines += [f"**Core skills:** {', '.join(profile['skills'])}", ""]

    if profile.get("projects"):
        lines.append("**Featured projects:**")
        for proj in profile["projects"]:
            link = proj.get("link") or "#"
            highlight = (proj.get("bullets") or [""])[0]
            lines.append(f"- [{proj.get('name', '')}]({link}) — {highlight}")
        lines.append("")

    contact_bits = []
    if contact.get("email"):
        contact_bits.append(f"📫 {contact['email']}")
    if contact.get("linkedin"):
        contact_bits.append(f"[LinkedIn]({contact['linkedin']})")
    if contact_bits:
        lines.append(" | ".join(contact_bits))

    lines += ["", "<!-- Auto-updated from profile.json by jobseeker's update-github-profile command -->"]
    return "\n".join(lines)


def update_github_profile(profile: dict) -> dict:
    """Creates (if needed) and updates the special `<username>/<username>` repo
    that GitHub renders on your profile page, plus your account bio. Returns a
    dict of what happened for the caller to report."""
    git_exe = _resolve_exe("git", GIT_EXE)
    gh_exe = _resolve_exe("gh", GH_EXE)

    username = extract_github_username(profile)
    if not username:
        raise ValueError(
            "No GitHub link found in profile.json's contact.other_links to derive your username from."
        )

    result = {"username": username, "created_repo": False, "readme_updated": False, "bio_updated": False}

    repo_slug = f"{username}/{username}"
    view = _run([gh_exe, "repo", "view", repo_slug])
    if view.returncode != 0:
        create = _run(
            [gh_exe, "repo", "create", repo_slug, "--public", "--description", "My developer profile"]
        )
        if create.returncode != 0:
            raise RuntimeError(f"Could not create profile repo '{repo_slug}': {create.stderr.strip()}")
        result["created_repo"] = True

    work_dir = config.DATA_DIR / "github_profile_repo"
    if not (work_dir / ".git").exists():
        work_dir.parent.mkdir(parents=True, exist_ok=True)
        if work_dir.exists():
            shutil.rmtree(work_dir)
        clone = _run([gh_exe, "repo", "clone", repo_slug, str(work_dir)])
        if clone.returncode != 0:
            raise RuntimeError(f"Could not clone profile repo: {clone.stderr.strip()}")

    readme = build_readme(profile)
    readme_path = work_dir / "README.md"
    previous = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    readme_path.write_text(readme, encoding="utf-8")

    if previous.strip() != readme.strip():
        _run([git_exe, "config", "user.email", profile.get("contact", {}).get("email", "")], cwd=str(work_dir))
        _run([git_exe, "config", "user.name", profile.get("contact", {}).get("name", "")], cwd=str(work_dir))
        _run([git_exe, "add", "-A"], cwd=str(work_dir))
        commit = _run(
            [git_exe, "commit", "-m", "Update profile README from jobseeker profile.json"], cwd=str(work_dir)
        )
        if commit.returncode == 0:
            push = _run([git_exe, "push"], cwd=str(work_dir))
            result["readme_updated"] = push.returncode == 0
            if push.returncode != 0:
                raise RuntimeError(f"Committed but could not push profile README: {push.stderr.strip()}")

    if profile.get("summary"):
        bio = profile["summary"][:160]
        bio_result = _run([gh_exe, "api", "-X", "PATCH", "user", "-f", f"bio={bio}"])
        result["bio_updated"] = bio_result.returncode == 0
        if bio_result.returncode != 0:
            raise RuntimeError(f"Could not update bio: {bio_result.stderr.strip()}")

    return result
