from jobseeker.job_alerts import _is_relevant, _relevance_keywords, _split_candidate_postings

SAMPLE_PROFILE = {
    "target_roles": ["Machine Learning Engineer", "NLP Engineer"],
    "skills": ["Python", "PyTorch", "LLMs"],
}


def test_relevance_keywords_derived_from_profile():
    keywords = _relevance_keywords(SAMPLE_PROFILE)
    assert "machine learning engineer" in keywords
    assert "python" in keywords


def test_is_relevant_matches_target_role():
    keywords = _relevance_keywords(SAMPLE_PROFILE)
    assert _is_relevant("New job: Machine Learning Engineer at Acme", "", keywords)


def test_is_relevant_rejects_unrelated():
    keywords = _relevance_keywords(SAMPLE_PROFILE)
    assert not _is_relevant("Your weekly newsletter digest", "unrelated content here", keywords)


def test_is_relevant_defaults_true_with_no_keywords():
    assert _is_relevant("anything", "anything", [])


def test_split_candidate_postings_filters_short_chunks():
    body = "short\n\n\n" + ("x" * 250) + "\n\n\nalso short"
    chunks = _split_candidate_postings(body)
    assert len(chunks) == 1
    assert len(chunks[0]) > 200
