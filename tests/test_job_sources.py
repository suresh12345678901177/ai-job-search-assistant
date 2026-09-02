from jobseeker.job_sources import _is_relevant, _keywords, _strip_html

PROFILE = {
    "target_roles": ["Machine Learning Engineer"],
    "skills": ["Python", "PyTorch"],
}


def test_keywords_derived_from_profile():
    kws = _keywords(PROFILE)
    assert "machine learning engineer" in kws
    assert "python" in kws


def test_is_relevant_matches():
    kws = _keywords(PROFILE)
    assert _is_relevant("Machine Learning Engineer", "", kws)


def test_is_relevant_rejects_unrelated():
    kws = _keywords(PROFILE)
    assert not _is_relevant("Sales Associate", "retail store position", kws)


def test_strip_html_removes_tags():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello  world"
