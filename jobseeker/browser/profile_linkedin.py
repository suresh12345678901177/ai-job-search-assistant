"""Semi-automated LinkedIn profile updates. Opens the edit panels and fills
in the suggested text, but never clicks Save - selectors for LinkedIn's
profile-edit modals shift often, so this is best-effort with a manual
fallback (the suggested text is always printed too)."""
from playwright.sync_api import Page

PROFILE_URL = "https://www.linkedin.com/in/me/"


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
            _fill_first_visible(
                page,
                ["input#single-line-text-form-component-headline", "input[id*='headline']"],
                suggestions.get("linkedin_headline", ""),
                "headline",
            )
            print("  headline field opened - review it, then click Save yourself. Not auto-saving.")
    except Exception as exc:
        print(f"  could not open intro editor automatically: {exc}")

    print(
        "\nFor the About section, click 'Add profile section' / the About pencil icon and paste "
        "the suggested text above - that modal's structure changes too often to fill reliably."
    )
