import shutil
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from . import config, llm_client

PROFILE_SCHEMA_INSTRUCTIONS = """
Extract the resume text into this exact JSON schema (use empty strings/lists where
information is genuinely absent, never invent content that is not in the source text):

{
  "contact": {"name": "", "email": "", "phone": "", "location": "", "linkedin": "", "other_links": []},
  "target_roles": [],
  "summary": "",
  "skills": [],
  "experience": [
    {"company": "", "title": "", "location": "", "start": "", "end": "", "bullets": []}
  ],
  "education": [
    {"institution": "", "degree": "", "location": "", "start": "", "end": "", "details": ""}
  ],
  "projects": [
    {"name": "", "description": "", "bullets": [], "link": ""}
  ],
  "certifications": [],
  "languages_spoken": [{"language": "", "level": ""}],
  "publications": [
    {"title": "", "venue": "", "date": "", "co_authored": false, "details": ""}
  ]
}

"target_roles" is not usually stated explicitly in a resume - leave it as an empty list;
the user can fill it in later. Preserve bullet wording faithfully but you may split
run-on bullets. Order experience/education most recent first as they appear in the source.
"""


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx_text(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(path)
    if suffix == ".docx":
        return _extract_docx_text(path)
    raise ValueError(f"Unsupported resume file type: {suffix} (use .pdf or .docx)")


def parse_resume(path: Path) -> dict:
    raw_text = extract_text(path).strip()
    if not raw_text:
        raise ValueError(
            "No text could be extracted from the resume file (it may be a scanned image)."
        )

    profile = llm_client.call_json(
        system=(
            "You are a precise resume-parsing engine. You convert raw resume text into "
            "structured JSON without adding, embellishing, or inferring facts that are not "
            "present in the source. " + PROFILE_SCHEMA_INSTRUCTIONS
        ),
        user=f"Resume text:\n\n{raw_text}",
        max_tokens=4096,
    )
    profile["_raw_text"] = raw_text
    return profile


def ingest(path: Path) -> dict:
    config.ensure_dirs()
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {path}")

    profile = parse_resume(path)

    dest = config.DATA_DIR / f"resume_original{path.suffix.lower()}"
    shutil.copy2(path, dest)

    import json

    with open(config.PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    return profile
