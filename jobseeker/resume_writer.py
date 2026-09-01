from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

HEADING_COLOR = RGBColor(0x1A, 0x1A, 0x1A)


def _add_heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = HEADING_COLOR
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    border_p = p._p.get_or_add_pPr()
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "888888")
    pbdr.append(bottom)
    border_p.append(pbdr)


def render_docx(profile: dict, out_path: Path) -> Path:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    for section in doc.sections:
        section.top_margin = Pt(36)
        section.bottom_margin = Pt(36)
        section.left_margin = Pt(46)
        section.right_margin = Pt(46)

    contact = profile.get("contact", {})
    name_p = doc.add_paragraph()
    name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_run = name_p.add_run(contact.get("name", "").strip() or "Your Name")
    name_run.bold = True
    name_run.font.size = Pt(18)

    contact_bits = [
        contact.get("email", ""),
        contact.get("phone", ""),
        contact.get("location", ""),
        contact.get("linkedin", ""),
        *contact.get("other_links", []),
    ]
    contact_line = " | ".join(b for b in contact_bits if b)
    if contact_line:
        contact_p = doc.add_paragraph()
        contact_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        contact_p.add_run(contact_line).font.size = Pt(9.5)

    if profile.get("summary"):
        _add_heading(doc, "Summary")
        doc.add_paragraph(profile["summary"])

    if profile.get("skills"):
        _add_heading(doc, "Skills")
        doc.add_paragraph(" • ".join(profile["skills"]))

    if profile.get("experience"):
        _add_heading(doc, "Experience")
        for exp in profile["experience"]:
            line = doc.add_paragraph()
            title_run = line.add_run(f"{exp.get('title', '')} — {exp.get('company', '')}")
            title_run.bold = True
            dates = " – ".join(x for x in (exp.get("start", ""), exp.get("end", "")) if x)
            meta_bits = [b for b in (exp.get("location", ""), dates) if b]
            if meta_bits:
                line.add_run("    " + " | ".join(meta_bits)).italic = True
            for bullet in exp.get("bullets", []):
                doc.add_paragraph(bullet, style="List Bullet")

    if profile.get("projects"):
        _add_heading(doc, "Projects")
        for proj in profile["projects"]:
            line = doc.add_paragraph()
            name_run = line.add_run(proj.get("name", ""))
            name_run.bold = True
            if proj.get("link"):
                line.add_run(f"  ({proj['link']})").italic = True
            if proj.get("description"):
                doc.add_paragraph(proj["description"])
            for bullet in proj.get("bullets", []):
                doc.add_paragraph(bullet, style="List Bullet")

    if profile.get("education"):
        _add_heading(doc, "Education")
        for edu in profile["education"]:
            line = doc.add_paragraph()
            deg_run = line.add_run(f"{edu.get('degree', '')} — {edu.get('institution', '')}")
            deg_run.bold = True
            dates = " – ".join(x for x in (edu.get("start", ""), edu.get("end", "")) if x)
            meta_bits = [b for b in (edu.get("location", ""), dates) if b]
            if meta_bits:
                line.add_run("    " + " | ".join(meta_bits)).italic = True
            if edu.get("details"):
                doc.add_paragraph(edu["details"])

    if profile.get("publications"):
        _add_heading(doc, "Publications")
        for pub in profile["publications"]:
            line = doc.add_paragraph()
            title_run = line.add_run(pub.get("title", ""))
            title_run.bold = True
            if pub.get("co_authored"):
                line.add_run(" (co-authored)").italic = True
            meta_bits = [b for b in (pub.get("venue", ""), pub.get("date", "")) if b]
            if meta_bits:
                doc.add_paragraph(" | ".join(meta_bits)).runs[0].italic = True
            if pub.get("details"):
                doc.add_paragraph(pub["details"])

    if profile.get("certifications"):
        _add_heading(doc, "Certifications")
        doc.add_paragraph(" • ".join(profile["certifications"]))

    if profile.get("languages_spoken"):
        _add_heading(doc, "Languages")
        bits = [
            f"{lang.get('language', '')} ({lang.get('level', '')})" if lang.get("level") else lang.get("language", "")
            for lang in profile["languages_spoken"]
            if lang.get("language")
        ]
        doc.add_paragraph(" • ".join(bits))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return out_path


def render_txt(profile: dict, out_path: Path) -> Path:
    """A plain-text rendering for ATS parsers that struggle with .docx layout."""
    lines: list[str] = []
    contact = profile.get("contact", {})
    lines.append(contact.get("name", ""))
    lines.append(
        " | ".join(
            b
            for b in (
                contact.get("email", ""),
                contact.get("phone", ""),
                contact.get("location", ""),
                contact.get("linkedin", ""),
                *contact.get("other_links", []),
            )
            if b
        )
    )
    lines.append("")

    if profile.get("summary"):
        lines += ["SUMMARY", profile["summary"], ""]

    if profile.get("skills"):
        lines += ["SKILLS", ", ".join(profile["skills"]), ""]

    if profile.get("experience"):
        lines.append("EXPERIENCE")
        for exp in profile["experience"]:
            dates = " - ".join(x for x in (exp.get("start", ""), exp.get("end", "")) if x)
            lines.append(f"{exp.get('title', '')} — {exp.get('company', '')} ({dates})")
            for bullet in exp.get("bullets", []):
                lines.append(f"  - {bullet}")
        lines.append("")

    if profile.get("projects"):
        lines.append("PROJECTS")
        for proj in profile["projects"]:
            lines.append(proj.get("name", ""))
            for bullet in proj.get("bullets", []):
                lines.append(f"  - {bullet}")
        lines.append("")

    if profile.get("education"):
        lines.append("EDUCATION")
        for edu in profile["education"]:
            dates = " - ".join(x for x in (edu.get("start", ""), edu.get("end", "")) if x)
            lines.append(f"{edu.get('degree', '')} — {edu.get('institution', '')} ({dates})")
        lines.append("")

    if profile.get("publications"):
        lines.append("PUBLICATIONS")
        for pub in profile["publications"]:
            suffix = " (co-authored)" if pub.get("co_authored") else ""
            meta_bits = [b for b in (pub.get("venue", ""), pub.get("date", "")) if b]
            meta = f" - {' | '.join(meta_bits)}" if meta_bits else ""
            lines.append(f"{pub.get('title', '')}{suffix}{meta}")
            if pub.get("details"):
                lines.append(f"  {pub['details']}")
        lines.append("")

    if profile.get("certifications"):
        lines += ["CERTIFICATIONS", ", ".join(profile["certifications"]), ""]

    if profile.get("languages_spoken"):
        bits = [
            f"{lang.get('language', '')} ({lang.get('level', '')})" if lang.get("level") else lang.get("language", "")
            for lang in profile["languages_spoken"]
            if lang.get("language")
        ]
        lines += ["LANGUAGES", ", ".join(bits)]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
