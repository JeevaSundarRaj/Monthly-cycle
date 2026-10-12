import re

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, expect

PHONE_RE = re.compile(r"\(\d{3}\)\s*\d{3}-\d{4}")


class GeoRoutingPage:
    """Office settings > Geo. Routing: create a router, read its number, delete it."""

    def __init__(self, page: Page):
        self.page = page

    def _click(self, locator, timeout=15000):
        locator.wait_for(state="visible", timeout=timeout)
        locator.click()

    def open(self):
        self.page.goto("https://dialpadbeta.com/officesettings")
        self._click(self.page.get_by_role("link", name="Geo. Routing"), timeout=30000)

    def delete_existing(self, name=None):
        """Delete routers named `name` (opened from the sidebar, since Delete only shows on a router's page)."""
        if name:
            router = self.page.get_by_role("link", name=name, exact=True)
            self.page.wait_for_timeout(2000)
            while router.count() > 0:
                router.first.click()
                self._click(self.page.get_by_role("button", name="Delete Geographic Router"))
                self._click(self.page.get_by_role("button", name="delete", exact=True))
                expect(self.page.get_by_text("Changes Saved!").first).to_be_visible(timeout=15000)
                self.page.wait_for_timeout(2000)
        delete_btn = self.page.get_by_role("button", name="Delete Geographic Router")
        while delete_btn.count() > 0 and delete_btn.first.is_visible():
            delete_btn.first.click()
            self._click(self.page.get_by_role("button", name="delete", exact=True))
            expect(self.page.get_by_text("Changes Saved!").first).to_be_visible(timeout=15000)
            self.page.wait_for_timeout(1000)

    def create_router(self, name):
        """Open the create dialog, name the router and wait for its page."""
        self.page.wait_for_timeout(2000)  # let the list re-render after deletions
        self._click(self.page.get_by_role("listitem").filter(has_text="Geo. Routing").get_by_role("button"))
        name_box = self.page.locator("#new-routing-target-name")
        create_btn = self.page.locator("#add-routing-target")
        for attempt in range(3):
            name_box.fill(name)
            self.page.wait_for_timeout(500)
            try:
                create_btn.click(timeout=10000)
                break
            except PlaywrightTimeoutError:
                if attempt == 2:
                    raise

        # the create dialog must close before the new router's page is clickable
        expect(self.page.locator("#overlay.app-overlay-add_routing_target")).to_be_hidden(timeout=30000)

    def add_number(self):
        """First step on a new router: add a local number."""
        self._click(self.page.get_by_role("button", name="Add a number"))
        self._click(self.page.get_by_role("button", name="Next"))
        self._click(self.page.get_by_role("button", name="Add number"))

    def create(self, name, area_code_prefix, route_to, fallback_to):
        """Create a router that sends `area_code_prefix` callers to `route_to`, everyone else to `fallback_to`."""
        self.create_router(name)
        self.add_number()

        self._click(self.page.locator("#add-rule div").first)
        self.page.get_by_role("textbox", name="Enter international format").fill(area_code_prefix)
        search = self.page.get_by_placeholder("Search by name")
        search.fill(route_to)
        self._click(self.page.get_by_text(f"{route_to} Contact Center"))
        self._click(self.page.get_by_role("button", name="Save Changes"))
        expect(self.page.get_by_role("button", name="Save Changes")).to_be_hidden(timeout=30000)
        self.page.wait_for_timeout(1000)  # drawer slide-out animation

        fallback_menu = self.page.locator(".fallback-menu > .select-menu-view > .select-menu > .sm-input-shim")
        fallback_menu.wait_for(state="visible", timeout=15000)
        try:
            fallback_menu.click(timeout=8000)
        except PlaywrightTimeoutError:
            # a lingering transparent #content-overlay can swallow the click
            fallback_menu.click(force=True)
        self._click(self.page.get_by_role("link", name=fallback_to, exact=True))

    def read_number(self):
        """The router's phone number as shown in the UI (digits only)."""
        row = self.page.locator("#dids-view tr.d-bb.d-bc-subtle").filter(has_text=PHONE_RE).first
        row.wait_for(state="visible", timeout=30000)
        match = PHONE_RE.search(row.inner_text())
        assert match, f"No phone number found in geo routing row: {row.inner_text()!r}"
        return re.sub(r"\D", "", match.group(0))
