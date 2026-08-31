from jobseeker.profile_suggest import _normalize_suggestions


def test_normalize_handles_list_where_string_expected():
    raw = {
        "linkedin_headline": "ML Engineer",
        "linkedin_about": ["Paragraph one.", "Paragraph two."],
        "linkedin_skills": ["Python", "LLMs"],
        "naukri_headline": "ML Engineer",
        "naukri_key_skills": "Python, LLMs, TensorFlow",
    }
    result = _normalize_suggestions(raw)
    assert result["linkedin_about"] == "Paragraph one.\n\nParagraph two."
    assert result["naukri_key_skills"] == ["Python", "LLMs", "TensorFlow"]


def test_normalize_handles_string_where_list_expected():
    raw = {
        "linkedin_headline": "ML Engineer",
        "linkedin_about": "One paragraph.",
        "linkedin_skills": "Python, LLMs",
        "naukri_headline": "ML Engineer",
        "naukri_key_skills": ["Python", "LLMs"],
    }
    result = _normalize_suggestions(raw)
    assert result["linkedin_about"] == "One paragraph."
    assert result["linkedin_skills"] == ["Python", "LLMs"]


def test_normalize_handles_missing_fields():
    result = _normalize_suggestions({})
    assert result["linkedin_headline"] == ""
    assert result["linkedin_about"] == ""
    assert result["linkedin_skills"] == []
