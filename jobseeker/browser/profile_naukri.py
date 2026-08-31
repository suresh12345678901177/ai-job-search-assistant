"""Semi-automated Naukri profile updates. Best-effort fill, never saves."""
from playwright.sync_api import Page

from .. import config


def update_headline_and_skills(page: Page, suggestions: dict) -> None:
    page.goto(config.NAUKRI_PROFILE_URL)
    page.wait_for_load_state("domcontentloaded")

    print("\nSuggested Naukri resume headline:\n  " + suggestions.get("naukri_headline", ""))
    print("\nSuggested Naukri key skills:")
    for skill in suggestions.get("naukri_key_skills", []):
        print(f"  - {skill}")

    try:
        edit_headline = page.locator("span:has-text('Resume headline') >> xpath=../.. >> a, i.edit").first
        if edit_headline.count() and edit_headline.is_visible(timeout=3000):
            edit_headline.click()
            page.wait_for_timeout(1000)
            textarea = page.locator("textarea").first
            if textarea.count():
                textarea.fill(suggestions.get("naukri_headline", ""))
                print("  headline field opened and filled - review it, then click Save yourself.")
    except Exception as exc:
        print(f"  could not open headline editor automatically: {exc}")
        print("  paste the suggested headline above manually via 'Resume headline' edit.")

    print(
        "\nFor Key Skills, use the 'Key skills' edit pencil and add the suggested skills above - "
        "that widget's autocomplete behavior makes reliable automation impractical."
    )
