"""Lightweight RAG retrieval over the user's growing knowledge base:
resume experience/project bullets, saved job descriptions, and past
application Q&A answers. TF-IDF + cosine similarity is used instead of a
neural embedding model - it needs no extra API key or GPU/torch install,
and is a good fit since ATS/recruiter keyword matching is itself
substantially keyword-driven.
"""
from dataclasses import dataclass

from . import store
from .tfidf import TfidfIndex


@dataclass
class Document:
    doc_type: str
    text: str
    meta: dict


def resume_documents(profile: dict) -> list[Document]:
    docs: list[Document] = []

    if profile.get("summary"):
        docs.append(Document("summary", profile["summary"], {"section": "summary"}))

    for exp in profile.get("experience", []):
        header = f"{exp.get('title', '')} at {exp.get('company', '')}"
        for bullet in exp.get("bullets", []):
            docs.append(
                Document(
                    "experience_bullet",
                    bullet,
                    {"company": exp.get("company", ""), "title": exp.get("title", ""), "header": header},
                )
            )

    for proj in profile.get("projects", []):
        base_meta = {"name": proj.get("name", "")}
        if proj.get("description"):
            docs.append(Document("project", proj["description"], base_meta))
        for bullet in proj.get("bullets", []):
            docs.append(Document("project_bullet", bullet, base_meta))

    if profile.get("skills"):
        docs.append(Document("skills", ", ".join(profile["skills"]), {"section": "skills"}))

    return docs


class RetrievalIndex:
    def __init__(self, documents: list[Document]):
        self.documents = documents
        self._index = TfidfIndex([d.text for d in documents])

    def query(self, text: str, top_k: int = 8, doc_types: set[str] | None = None) -> list[tuple[Document, float]]:
        if not self.documents:
            return []
        scores = self._index.query(text)
        ranked = sorted(
            ((doc, float(score)) for doc, score in zip(self.documents, scores)),
            key=lambda pair: pair[1],
            reverse=True,
        )
        if doc_types:
            ranked = [pair for pair in ranked if pair[0].doc_type in doc_types]
        return [pair for pair in ranked if pair[1] > 0][:top_k]


def build_resume_index(profile: dict) -> RetrievalIndex:
    return RetrievalIndex(resume_documents(profile))


def top_resume_matches(profile: dict, jd_text: str, top_k: int = 10) -> list[tuple[Document, float]]:
    return build_resume_index(profile).query(jd_text, top_k=top_k)


def build_qa_index() -> tuple[RetrievalIndex, list[dict]]:
    bank = store.load_qa_bank()
    docs = [Document("qa", entry["question"], entry) for entry in bank]
    return RetrievalIndex(docs), bank


def top_qa_matches(question: str, top_k: int = 3) -> list[dict]:
    index, _ = build_qa_index()
    ranked = index.query(question, top_k=top_k)
    return [doc.meta for doc, _ in ranked]


def format_matches_for_prompt(matches: list[tuple[Document, float]]) -> str:
    lines = []
    for doc, score in matches:
        tag = doc.meta.get("header") or doc.meta.get("name") or doc.doc_type
        lines.append(f"- [{tag}] {doc.text}")
    return "\n".join(lines)
