from jobseeker.profile_update import apply_update

BASE_PROFILE = {
    "summary": "ML engineer.",
    "skills": ["Python", "TensorFlow"],
    "experience": [{"company": "DOT-C", "title": "ML Engineer Intern", "bullets": ["Built models."]}],
    "projects": [],
    "certifications": [],
}


def test_apply_update_adds_new_skill_and_bullet():
    plan = {
        "summary_update": None,
        "new_skills": ["Docker"],
        "experience_updates": [{"company": "DOT-C", "add_bullets": ["Containerized the app with Docker."]}],
        "new_projects": [],
        "new_certifications": [],
    }
    updated, changes = apply_update(BASE_PROFILE, plan)

    assert "Docker" in updated["skills"]
    assert "Containerized the app with Docker." in updated["experience"][0]["bullets"]
    assert len(changes) == 2
    # original untouched
    assert BASE_PROFILE["skills"] == ["Python", "TensorFlow"]


def test_apply_update_skips_duplicates():
    plan = {"new_skills": ["Python"], "experience_updates": [], "new_projects": [], "new_certifications": []}
    updated, changes = apply_update(BASE_PROFILE, plan)
    assert updated["skills"] == ["Python", "TensorFlow"]
    assert changes == []


def test_apply_update_ignores_unknown_company():
    plan = {"experience_updates": [{"company": "NotARealCompany", "add_bullets": ["should not be added"]}]}
    updated, changes = apply_update(BASE_PROFILE, plan)
    assert updated["experience"][0]["bullets"] == ["Built models."]
    assert changes == []


def test_apply_update_adds_new_project():
    plan = {"new_projects": [{"name": "New Thing", "description": "", "bullets": ["Did X"], "link": ""}]}
    updated, changes = apply_update(BASE_PROFILE, plan)
    assert updated["projects"][0]["name"] == "New Thing"
    assert "Added project: New Thing" in changes


def test_apply_update_summary_replaces_when_given():
    plan = {"summary_update": "New rewritten summary."}
    updated, changes = apply_update(BASE_PROFILE, plan)
    assert updated["summary"] == "New rewritten summary."
