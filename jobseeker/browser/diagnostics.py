"""Debugging helper for when LinkedIn/Naukri change their markup and the
profile-automation selectors stop working. Screenshots the real, logged-in
page and dumps every button's aria-label/text so the actual selectors can be
read off directly instead of guessed at."""
from pathlib import Path

from playwright.sync_api import Page

from .. import config


def dump_page(page: Page, url: str, out_prefix: str) -> tuple[Path, Path]:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    page.goto(url)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(3000)

    screenshot_path = config.DATA_DIR / f"debug_{out_prefix}.png"
    page.screenshot(path=str(screenshot_path))

    buttons_path = config.DATA_DIR / f"debug_{out_prefix}_buttons.txt"
    with open(buttons_path, "w", encoding="utf-8") as f:
        for b in page.locator("button").all()[:300]:
            try:
                label = b.get_attribute("aria-label") or ""
                text = b.inner_text().strip()[:60].replace("\n", " ")
                if label or text:
                    f.write(f"aria-label={label!r}  text={text!r}\n")
            except Exception:
                continue

    return screenshot_path, buttons_path


def dump_linkedin_profile(page: Page) -> tuple[Path, Path]:
    from .profile_linkedin import PROFILE_URL

    return dump_page(page, PROFILE_URL, "linkedin_profile")


def dump_naukri_profile(page: Page) -> tuple[Path, Path]:
    return dump_page(page, config.NAUKRI_PROFILE_URL, "naukri_profile")
