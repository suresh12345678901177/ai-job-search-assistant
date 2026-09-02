from jobseeker.job_alerts import (
    _extract_job_url,
    _html_to_text_with_links,
    _is_relevant,
    _relevance_keywords,
    _split_candidate_postings,
)

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


def test_extract_job_url_prefers_linkedin_over_tracking_link():
    chunk = (
        "Machine Learning Engineer at Acme\n"
        "View job (https://www.linkedin.com/jobs/view/12345)\n"
        "Unsubscribe (https://email.linkedin.com/unsub?x=1)"
    )
    assert _extract_job_url(chunk) == "https://www.linkedin.com/jobs/view/12345"


def test_extract_job_url_falls_back_to_first_url():
    chunk = "Backend Engineer at Acme\nApply (https://boards.greenhouse.io/acme/jobs/1)"
    assert _extract_job_url(chunk) == "https://boards.greenhouse.io/acme/jobs/1"


def test_extract_job_url_empty_when_no_links():
    assert _extract_job_url("just some text with no links") == ""


def test_html_to_text_with_links_inlines_href_next_to_text():
    html = '<p>New job: <a href="https://www.naukri.com/job/123">View job</a></p>'
    text = _html_to_text_with_links(html)
    assert "https://www.naukri.com/job/123" in text
    assert "View job" in text
