from docx import Document

from jobseeker.resume_writer import render_docx, render_txt

SAMPLE_PROFILE = {
    "contact": {"name": "Jane Doe", "email": "jane@example.com", "phone": "555-1234"},
    "summary": "Experienced backend engineer.",
    "skills": ["Python", "SQL"],
    "experience": [
        {
            "company": "Acme",
            "title": "Backend Engineer",
            "start": "2020",
            "end": "Present",
            "bullets": ["Built a Python API", "Optimized SQL queries"],
        }
    ],
    "education": [{"institution": "State University", "degree": "B.S. Computer Science"}],
    "projects": [],
    "certifications": [],
}


def test_render_docx_contains_expected_text(tmp_path):
    out_path = render_docx(SAMPLE_PROFILE, tmp_path / "resume.docx")
    assert out_path.exists()

    doc = Document(str(out_path))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Jane Doe" in full_text
    assert "Built a Python API" in full_text
    assert "Backend Engineer" in full_text
    assert "State University" in full_text


def test_render_txt_contains_expected_text(tmp_path):
    out_path = render_txt(SAMPLE_PROFILE, tmp_path / "resume.txt")
    text = out_path.read_text(encoding="utf-8")
    assert "Jane Doe" in text
    assert "SUMMARY" in text
    assert "Optimized SQL queries" in text
