from jobseeker.retrieval import RetrievalIndex, resume_documents


def test_resume_documents_extracts_bullets():
    profile = {
        "summary": "Backend engineer.",
        "experience": [
            {
                "company": "Acme",
                "title": "Backend Engineer",
                "bullets": ["Built a Python API", "Optimized SQL queries"],
            }
        ],
        "projects": [{"name": "Widget", "description": "A widget", "bullets": ["Used React"]}],
        "skills": ["Python", "SQL"],
    }
    docs = resume_documents(profile)
    texts = [d.text for d in docs]
    assert "Built a Python API" in texts
    assert "Optimized SQL queries" in texts
    assert any(d.doc_type == "skills" for d in docs)


def test_retrieval_ranks_relevant_bullet_first():
    profile = {
        "experience": [
            {
                "company": "Acme",
                "title": "Engineer",
                "bullets": [
                    "Built distributed Python microservices handling millions of requests",
                    "Organized quarterly team offsite events",
                ],
            }
        ]
    }
    index = RetrievalIndex(resume_documents(profile))
    results = index.query("Looking for a Python microservices backend engineer", top_k=2)
    assert results, "expected at least one match"
    assert "Python microservices" in results[0][0].text


def test_empty_index_returns_no_matches():
    index = RetrievalIndex([])
    assert index.query("anything") == []
