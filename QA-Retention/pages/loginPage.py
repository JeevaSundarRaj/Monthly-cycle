from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
import json


class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.locators = None

    def login(self, email: str, password: str, url: str = "https://dialpadbeta.com/app"):
        with open('pages/elements/locators.json') as f:
            self.locators = json.load(f)

        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except PlaywrightTimeoutError:
            print("Navigation timed out, retrying...")
            self.page.goto(url, wait_until="domcontentloaded", timeout=60000)

        self.page.wait_for_timeout(3000)

        body_text = self.page.locator("body").text_content() or ""

        if len(body_text.strip()) < 50:
            print("Blank page observed, reloading...")
            self.page.reload()
            self.page.wait_for_load_state("networkidle")

        self.page.locator(self.locators['loginEmail']).fill(email)
        self.page.locator(self.locators['loginPassword']).fill(password)
        self.page.locator(self.locators['loginButton']).click()
