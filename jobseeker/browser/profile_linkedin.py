"""Semi-automated LinkedIn profile updates. The headline field is reliably
auto-fillable, so it's filled AND auto-saved - it's your own reversible
profile text, not something sent to a third party, so the extra click isn't
worth pausing for. The About section and skills widgets are NOT auto-saved:
their selectors shift too often for a blind auto-save to be safe (a broken
partial paste going live on your public profile is the realistic failure
mode there), so those stay print-and-paste-yourself."""
from playwright.sync_api import Page

PROFILE_URL = "https://www.linkedin.com/in/me/"

SAVE_BUTTON_SELECTORS = [
    "button[aria-label='Save']",
    "div.artdeco-modal__actionbar button:has-text('Save')",
    "button:has-text('Save')",
]


def _fill_first_visible(page: Page, selectors: list[str], value: str, field_name: str) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible(timeout=2000):
                loc.fill(value)
                print(f"  filled {field_name}")
                return True
        except Exception:
            continue
    print(f"  could not auto-fill {field_name} - copy it in manually (see printed text below)")
    return False


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


def update_intro_and_about(page: Page, suggestions: dict) -> None:
    page.goto(PROFILE_URL)
    page.wait_for_load_state("domcontentloaded")

    print("\nSuggested LinkedIn headline:\n  " + suggestions.get("linkedin_headline", ""))
    print("\nSuggested LinkedIn About:\n" + suggestions.get("linkedin_about", ""))
    print("\nSuggested skills to pin (add via 'Add profile section' > Skills):")
    for skill in suggestions.get("linkedin_skills", []):
        print(f"  - {skill}")

    try:
        edit_intro = page.locator("button[aria-label*='Edit intro']").first
        if edit_intro.count() and edit_intro.is_visible(timeout=3000):
            edit_intro.click()
            page.wait_for_timeout(1000)
            filled = _fill_first_visible(
                page,
                ["input#single-line-text-form-component-headline", "input[id*='headline']"],
                suggestions.get("linkedin_headline", ""),
                "headline",
            )
            if filled:
                page.wait_for_timeout(300)
                _try_click_save(page)
            else:
                print("  headline field opened - paste it in and click Save yourself.")
    except Exception as exc:
        print(f"  could not open intro editor automatically: {exc}")

    print(
        "\nFor the About section, click 'Add profile section' / the About pencil icon and paste "
        "the suggested text above - that modal's structure changes too often to fill reliably."
    )
