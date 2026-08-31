"""Playwright session handling.

Login is always done manually by the user in a real, visible browser window -
this code never sees or stores a password. It only persists the resulting
session cookies (storage_state) so future commands can reuse the login.
"""
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import sync_playwright

from .. import config

SITE_URLS = {
    "linkedin": config.LINKEDIN_LOGIN_URL,
    "naukri": config.NAUKRI_LOGIN_URL,
}


def _state_path(site: str) -> Path:
    return config.SESSIONS_DIR / f"{site}_state.json"


def has_session(site: str) -> bool:
    return _state_path(site).exists()


def login(site: str) -> None:
    if site not in SITE_URLS:
        raise ValueError(f"Unknown site '{site}'. Expected one of {list(SITE_URLS)}")
    config.ensure_dirs()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(SITE_URLS[site])
        print(f"\nA browser window has opened at the {site} login page.")
        print("Log in manually (including any 2FA/captcha), then come back here.")
        input("Press Enter once you are fully logged in... ")
        context.storage_state(path=str(_state_path(site)))
        browser.close()
    print(f"Session saved for {site}. You can now run apply/update-profile for this site.")


@contextmanager
def open_session(site: str, headless: bool = False):
    if not has_session(site):
        raise RuntimeError(f"No saved session for {site}. Run `login {site}` first.")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=str(_state_path(site)))
        page = context.new_page()
        try:
            yield page
        finally:
            context.storage_state(path=str(_state_path(site)))
            browser.close()
