"""Semi-automated Naukri apply filling.

Naukri's apply flow is simpler than LinkedIn's in most cases (often a single
"Apply" click, sometimes followed by a short chatbot-style question flow) but
varies by employer. This fills text/chatbot questions it can confidently
answer and always stops before any final submit-like action.
"""
from pathlib import Path

from playwright.sync_api import Page

from .. import tailor

APPLY_BUTTON_SELECTORS = [
    "#apply-button",
    "button:has-text('Apply')",
    "a:has-text('Apply')",
]
CHATBOT_INPUT_SELECTORS = [
    "textarea.chatbot_InputBox",
    "div.chatbot_MessageBubble input[type='text']",
]
SEND_LIKE_SELECTORS = [
    "div.sendMsg",
    "button:has-text('Send')",
]


def _try_upload_resume(page: Page, resume_path: Path) -> None:
    file_inputs = page.locator("input[type='file']")
    if file_inputs.count():
        try:
            file_inputs.first.set_input_files(str(resume_path))
            print(f"  uploaded resume: {resume_path.name}")
        except Exception as exc:
            print(f"  could not upload resume: {exc}")


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
        except Exception:
            continue

    if not clicked:
        print("Could not find an Apply button automatically. The tailored resume/cover letter")
        print("are in data/generated/ - please open the job and apply manually.")
        return

    page.wait_for_timeout(1500)
    _try_upload_resume(page, resume_path)

    for round_ in range(1, 8):
        page.wait_for_timeout(1000)
        question_box = None
        for sel in CHATBOT_INPUT_SELECTORS:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                question_box = loc
                break
        if not question_box:
            break

        question_text = ""
        try:
            bubbles = page.locator("div.chatbot_MessageBubble, div.botMsg")
            if bubbles.count():
                question_text = bubbles.last.inner_text().strip()
        except Exception:
            pass

        if not question_text:
            print("A chatbot question appeared but its text could not be read - please answer it manually.")
            break

        print(f"\nNaukri is asking: {question_text}")
        lowered = question_text.lower()
        if any(k in lowered for k in ("visa", "sponsor", "authoriz", "notice period", "salary", "ctc")):
            print("  this looks like a decision field (visa/salary/notice period) - please answer it yourself.")
            break

        answer = tailor.draft_answer(question_text, profile, job)
        try:
            question_box.fill(answer)
            print(f"  drafted answer: {answer}")
        except Exception as exc:
            print(f"  could not fill answer: {exc}")
            break

        print("  STOPPING before sending - review the drafted answer in the browser and click Send yourself.")
        return

    print("\nReview the application in the browser window and submit/send it yourself when ready.")
