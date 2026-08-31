"""Semi-automated LinkedIn Easy Apply filling.

This never clicks the final "Submit application" button - it fills what it
confidently can and stops for human review. LinkedIn's DOM changes fairly
often, so selectors here are best-effort: failures on any one field are
caught and logged rather than crashing the whole flow.

Fields with real consequences (work authorization, sponsorship, salary,
yes/no radios, dropdowns) are deliberately left untouched for the human to
answer, rather than guessed at.
"""
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PWTimeoutError

from .. import tailor

APPLY_BUTTON_SELECTORS = [
    "button.jobs-apply-button",
    "button:has-text('Easy Apply')",
]
NEXT_LIKE_SELECTORS = [
    "button:has-text('Next')",
    "button:has-text('Continue to next step')",
    "button:has-text('Review')",
]
SUBMIT_SELECTORS = [
    "button:has-text('Submit application')",
]


def _try_fill_text_fields(page: Page, profile: dict, job: dict) -> None:
    contact = profile.get("contact", {})
    field_map = {
        "email": contact.get("email", ""),
        "phone": contact.get("phone", ""),
        "mobile": contact.get("phone", ""),
    }

    inputs = page.locator(
        "div.jobs-easy-apply-modal input[type='text'], "
        "div.jobs-easy-apply-modal input[type='tel'], "
        "div.jobs-easy-apply-modal input[type='email'], "
        "div.jobs-easy-apply-modal textarea"
    )
    count = inputs.count()
    for i in range(count):
        field = inputs.nth(i)
        try:
            if (field.input_value() or "").strip():
                continue
        except Exception:
            continue

        label_text = ""
        try:
            field_id = field.get_attribute("id")
            if field_id:
                label = page.locator(f"label[for='{field_id}']")
                if label.count():
                    label_text = label.first.inner_text().strip()
        except Exception:
            pass

        if not label_text:
            continue

        lowered = label_text.lower()
        matched_value = next((v for k, v in field_map.items() if k in lowered and v), None)

        try:
            if matched_value:
                field.fill(matched_value)
                print(f"  filled '{label_text}' from profile")
            else:
                answer = tailor.draft_answer(label_text, profile, job)
                field.fill(answer)
                print(f"  drafted answer for '{label_text}' (review this before submitting)")
        except Exception as exc:
            print(f"  could not fill '{label_text}': {exc}")


def _try_upload_resume(page: Page, resume_path: Path) -> None:
    file_inputs = page.locator("div.jobs-easy-apply-modal input[type='file']")
    if file_inputs.count():
        try:
            file_inputs.first.set_input_files(str(resume_path))
            print(f"  uploaded resume: {resume_path.name}")
        except Exception as exc:
            print(f"  could not upload resume: {exc}")


def _flag_decision_fields(page: Page) -> None:
    selects = page.locator("div.jobs-easy-apply-modal select")
    radios = page.locator("div.jobs-easy-apply-modal fieldset")
    for group, kind in ((selects, "dropdown"), (radios, "radio/checkbox group")):
        for i in range(group.count()):
            try:
                text = group.nth(i).inner_text().strip().splitlines()[0]
            except Exception:
                text = "(unlabeled)"
            print(f"  needs your input ({kind}): {text}")


def apply_to_job(page: Page, job: dict, profile: dict, resume_path: Path) -> None:
    page.goto(job["url"])
    page.wait_for_load_state("domcontentloaded")

    clicked = False
    for sel in APPLY_BUTTON_SELECTORS:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=3000):
                btn.click()
                clicked = True
                break
        except PWTimeoutError:
            continue
        except Exception:
            continue

    if not clicked:
        print("Could not find an Easy Apply button automatically. Open the job and click Apply yourself,")
        print("then re-run with the modal open, or fill it out manually - the tailored resume/answers")
        print("are still available in data/generated/ for you to copy from.")
        return

    for step in range(1, 11):
        page.wait_for_timeout(1200)
        print(f"\nStep {step}:")

        _try_upload_resume(page, resume_path)
        _try_fill_text_fields(page, profile, job)
        _flag_decision_fields(page)

        submit_btn = None
        for sel in SUBMIT_SELECTORS:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                submit_btn = loc
                break
        if submit_btn:
            print("\nReached the final review step. STOPPING here on purpose - review everything")
            print("in the browser window, answer any flagged fields above, and click")
            print("'Submit application' yourself when you're ready.")
            return

        advanced = False
        for sel in NEXT_LIKE_SELECTORS:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                loc.click()
                advanced = True
                break
        if not advanced:
            print("No further 'Next' button found - the application may already be on the last step,")
            print("or the page layout differs from what this script expects. Please finish it manually.")
            return

    print("Stopped after 10 steps as a safety limit - please finish the rest manually.")
