from jobseeker.github_profile import build_readme, extract_github_username

SAMPLE_PROFILE = {
    "contact": {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "linkedin": "https://www.linkedin.com/in/janedoe",
        "other_links": ["https://github.com/janedoe123/some-repo"],
    },
    "target_roles": ["Machine Learning Engineer"],
    "summary": "ML engineer who builds things.",
    "skills": ["Python", "PyTorch"],
    "projects": [
        {"name": "Cool Project", "bullets": ["Built a thing that does X."], "link": "https://github.com/janedoe123/cool-project"}
    ],
}


def test_extract_github_username_from_other_links():
    assert extract_github_username(SAMPLE_PROFILE) == "janedoe123"


def test_extract_github_username_missing():
    assert extract_github_username({"contact": {"other_links": []}}) is None


def test_build_readme_contains_expected_content():
    readme = build_readme(SAMPLE_PROFILE)
    assert "Jane Doe" in readme
    assert "ML engineer who builds things." in readme
    assert "Machine Learning Engineer" in readme
    assert "Python, PyTorch" in readme
    assert "Cool Project" in readme
    assert "jane@example.com" in readme
