import re

from playwright.sync_api import Page


class ContactCenterPage:
    """Office settings > Contact Centers > <cc> > Business hours and call handling."""

    ALWAYS = "Always take calls (24/7)"
    SPECIFIC = "Only during specific hours"

    def __init__(self, page: Page):
        self.page = page

    def _click(self, locator, timeout=15000):
        locator.wait_for(state="visible", timeout=timeout)
        locator.click()

    def open_business_hours(self, cc_name):
        self.page.goto("https://dialpadbeta.com/officesettings")
        self._click(self.page.get_by_role("link", name="Contact Centers"), timeout=30000)
        self._click(self.page.get_by_text(cc_name, exact=True).first)
        self._click(self.page.get_by_text("Business hours and call").first)
        self._radio(self.ALWAYS).wait_for(state="visible", timeout=15000)

    def _radio(self, name):
        return self.page.get_by_role("radio", name=name)

    def _select(self, name):
        radio = self._radio(name)
        if not radio.is_checked():
            radio.check()
            # the setting autosaves; the toast is best-effort so a missed one doesn't fail the step
            try:
                self.page.get_by_text("Changes Saved!").first.wait_for(state="visible", timeout=10000)
            except Exception:
                pass
            self.page.wait_for_timeout(1000)

    def set_always_open(self):
        self._select(self.ALWAYS)

    def set_specific_hours(self):
        self._select(self.SPECIFIC)

    def is_always_open(self):
        return self._radio(self.ALWAYS).is_checked()

    def is_specific_hours(self):
        return self._radio(self.SPECIFIC).is_checked()

    def reload(self):
        """Reload and return to the business-hours view, to prove the setting persisted."""
        self.page.reload()
        self._click(self.page.get_by_text("Business hours and call").first, timeout=30000)
        self._radio(self.ALWAYS).wait_for(state="visible", timeout=15000)
