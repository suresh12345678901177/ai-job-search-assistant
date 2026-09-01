"""Semi-automated Naukri profile updates. The headline field is reliably
auto-fillable, so it's filled AND auto-saved - it's your own reversible
profile text, not something sent to a third party, so the extra click isn't
worth pausing for. Key skills is NOT auto-saved: its autocomplete widget
makes a blind auto-save unsafe, so that stays print-and-paste-yourself."""
from playwright.sync_api import Page

from .. import config

SAVE_BUTTON_SELECTORS = [
    "button:has-text('Save')",
    "button.saveBtn",
    "div.saveBtn",
]


def _try_click_save(page: Page) -> bool:
    for sel in SAVE_BUTTON_SELECTORS:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible(timeout=2000) and loc.is_enabled():
                loc.click()
                print("  clicked Save")
                return True
        except Exception:
            continue
    print("  could not find a Save button automatically - click Save yourself.")
    return False


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
                print("  filled headline")
                page.wait_for_timeout(300)
                _try_click_save(page)
            else:
                print("  headline editor opened but no text field found - paste it in yourself.")
    except Exception as exc:
        print(f"  could not open headline editor automatically: {exc}")
        print("  paste the suggested headline above manually via 'Resume headline' edit.")

    print(
        "\nFor Key Skills, use the 'Key skills' edit pencil and add the suggested skills above - "
        "that widget's autocomplete behavior makes reliable automation impractical."
    )
