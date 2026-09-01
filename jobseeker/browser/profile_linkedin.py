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


def _robust_click(locator, timeout: int = 5000) -> bool:
    """A plain click, falling back to force=True if something (LinkedIn's chat
    widget, a sticky header, a cookie banner) is intercepting pointer events -
    a common failure mode on LinkedIn's dynamic layout, not a real disagreement
    about whether the element is clickable."""
    try:
        locator.scroll_into_view_if_needed(timeout=timeout)
    except Exception:
        pass
    try:
        locator.click(timeout=timeout)
        return True
    except Exception:
        try:
            locator.click(timeout=timeout, force=True)
            return True
        except Exception:
            return False


def _try_click_save(page: Page) -> bool:
    for sel in SAVE_BUTTON_SELECTORS:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible(timeout=2000) and loc.is_enabled():
                if _robust_click(loc):
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
            if not _robust_click(edit_intro):
                print("  found the 'Edit intro' button but could not click it - open it manually.")
            else:
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
        else:
            print("  could not find the 'Edit intro' button automatically - "
                  "open your profile's intro pencil icon and paste the headline yourself.")
    except Exception as exc:
        print(f"  could not open intro editor automatically: {exc}")

    print(
        "\nFor the About section, click 'Add profile section' / the About pencil icon and paste "
        "the suggested text above - that modal's structure changes too often to fill reliably."
    )


def set_open_to_work(page: Page, profile: dict) -> None:
    """Sets LinkedIn's 'Open to Work' job preferences, visible to recruiters
    only (not broadcast to your network/employer) - a discreet, reversible,
    own-account setting, not a public post. Job title/location fields are
    autocomplete widgets that are inherently harder to automate reliably
    than a plain text input, so this degrades to manual instructions on any
    step it can't complete confidently rather than guessing."""
    page.goto(PROFILE_URL)
    page.wait_for_load_state("domcontentloaded")

    target_roles = profile.get("target_roles") or []
    location = profile.get("contact", {}).get("location", "")
    print("\nSetting Open to Work for:")
    print(f"  Job titles: {', '.join(target_roles) or '(none set in your profile)'}")
    print(f"  Location: {location or '(none set in your profile)'}")
    print("  Visibility: Recruiters only (not your network/employer)")

    try:
        open_to_button = page.locator("button:has-text('Open to')").first
        if not (open_to_button.count() and open_to_button.is_visible(timeout=3000)):
            print("  could not find the 'Open to' button automatically - set this up manually via "
                  "your profile > 'Open to' > Finding a new job.")
            return
        if not _robust_click(open_to_button):
            print("  found the 'Open to' button but something on the page blocked clicking it "
                  "(likely a chat widget or banner overlay) - set this up manually.")
            return
        page.wait_for_timeout(800)

        finding_job = page.locator("button:has-text('Finding a new job'), div:has-text('Finding a new job')").first
        if finding_job.count() and finding_job.is_visible(timeout=2000):
            _robust_click(finding_job)
            page.wait_for_timeout(800)

        if target_roles:
            title_input = page.locator("input[id*='TITLE'], input[placeholder*='title' i]").first
            if title_input.count() and title_input.is_visible(timeout=2000):
                for role in target_roles[:3]:
                    title_input.fill(role)
                    page.wait_for_timeout(600)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(400)
                print("  filled job titles")
            else:
                print("  could not find the job title field automatically - add titles manually.")

        if location:
            location_input = page.locator("input[id*='LOCATION'], input[placeholder*='location' i]").first
            if location_input.count() and location_input.is_visible(timeout=2000):
                location_input.fill(location)
                page.wait_for_timeout(600)
                page.keyboard.press("Enter")
                print("  filled location")
            else:
                print("  could not find the location field automatically - add location manually.")

        recruiters_only = page.locator("text=Recruiters only").first
        if recruiters_only.count() and recruiters_only.is_visible(timeout=2000):
            _robust_click(recruiters_only)
            print("  set visibility to Recruiters only")
        else:
            print("  could not find the visibility option automatically - set it to 'Recruiters only' "
                  "yourself if that's what you want (default may be broader).")

        if _try_click_save(page):
            print("  Open to Work saved")
        else:
            print("  review the Open to Work panel and click Save/Add yourself.")
    except Exception as exc:
        print(f"  could not complete Open to Work automatically ({exc}) - "
              "set it up manually via your profile > 'Open to' > Finding a new job.")
