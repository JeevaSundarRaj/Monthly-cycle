import re

from playwright.sync_api import Page, expect


class AiSettingsPage:
    """Office settings > Dialpad AI: Live Coach Cards and Custom Moments."""

    CARD_LIST_DROPDOWN = ".base-button__button.d-btn.d-btn--circle.d-btn--icon-only.bclr__dropdown-button"

    def __init__(self, page: Page):
        self.page = page

    def _click(self, locator, timeout=15000):
        locator.wait_for(state="visible", timeout=timeout)
        locator.click()

    def _name_box(self):
        # LCC form also has a "Name link" box, so the name match must be exact
        return self.page.get_by_role("textbox", name="Name", exact=True)

    def _keywords_box(self):
        return self.page.get_by_role("textbox", name="Press Enter or comma after")

    def _create_button(self, card_type):
        # the empty-state LCC page labels the button "Create AI Live Coach Card"; once cards exist it is "Create"
        plain = self.page.get_by_role("button", name="Create", exact=True)
        if card_type == "lcc":
            return plain.or_(self.page.get_by_role("button", name="Create AI Live Coach Card"))
        return plain

    def ensure_office_settings(self):
        # the login ?c=/officesettings redirect is not always honoured and can land on the app feed
        self.page.wait_for_url(re.compile(r"dialpadbeta\.com/(app|officesettings)"), timeout=60000)
        if "/officesettings" not in self.page.url:
            self.page.goto("https://dialpadbeta.com/officesettings")
        expect(self.page.get_by_role("link", name="Dialpad AI")).to_be_visible(timeout=30000)

    def go_to_dialpad_ai(self):
        self._click(self.page.get_by_role("link", name="Dialpad AI"))

    def open_live_coach_cards(self):
        self.go_to_dialpad_ai()
        expect(self._create_button("lcc")).to_be_visible(timeout=15000)

    def open_custom_moments(self):
        self.go_to_dialpad_ai()
        self._click(self.page.get_by_text("Custom Moments"))
        expect(self._create_button("cm")).to_be_visible(timeout=15000)

    TEMPLATE_CARD = "//span[normalize-space(.)='Authority']/parent::div"

    def start_create(self, card_type, from_template=False):
        self._click(self._create_button(card_type))
        if from_template:
            self._click(self.page.locator(self.TEMPLATE_CARD))
        else:
            self._click(self.page.get_by_role("button", name="Create from scratch"))
        expect(self._name_box()).to_be_visible(timeout=15000)
        expect(self.page.get_by_role("button", name="Create card")).to_be_visible(timeout=15000)

    def fill_name(self, name):
        box = self._name_box()
        box.wait_for(state="visible", timeout=15000)
        box.fill(name)
        expect(box).to_have_value(name)

    def select_language(self, code="en"):
        select = self.page.get_by_label("Please select a")
        select.select_option(code)
        expect(select).to_have_value(code)

    def fill_description(self, text):
        box = self.page.get_by_role("textbox", name="Description (Optional)")
        box.fill(text)
        expect(box).to_have_value(text)

    def fill_rep_response(self, text):
        box = self.page.get_by_role("textbox", name="Rep response")
        box.fill(text)
        expect(box).to_have_value(text)

    def add_link(self, url, link_name):
        url_box = self.page.get_by_role("textbox", name="Add a link (Optional) Paste")
        name_box = self.page.get_by_role("textbox", name="Name link", exact=True)
        url_box.fill(url)
        name_box.fill(link_name)
        expect(url_box).to_have_value(url)
        expect(name_box).to_have_value(link_name)

    def add_keywords(self, *keywords):
        box = self._keywords_box()
        for word in keywords:
            box.fill(word)
            box.press("Enter")
            expect(self.page.get_by_text(word, exact=True).first).to_be_visible(timeout=5000)
            expect(box).to_have_value("")

    def assert_duplicate_keyword_rejected(self, keyword):
        box = self._keywords_box()
        box.fill(keyword)
        expect(self.page.get_by_text("Keyword already added")).to_be_visible(timeout=5000)
        box.fill("")
        expect(self.page.get_by_text("Keyword already added")).to_have_count(0, timeout=5000)

    def assign_group(self, group_name):
        self._click(self.page.get_by_role("button", name="Assign groups"))
        self._click(self.page.get_by_text(group_name, exact=True))
        self._click(self.page.get_by_role("button", name="Update"))
        expect(self.page.get_by_text("Updated the assigned groups").first).to_be_visible(timeout=10000)
        expect(self.page.get_by_text(group_name, exact=True).first).to_be_visible(timeout=10000)

    def create_card(self, name=None):
        self._click(self.page.get_by_role("button", name="Create card"))
        if name:
            # toast prefix differs per card type ("AI Live Coach Card", ...), so match the tail only
            expect(self.page.get_by_text(f'"{name}" created!')).to_be_visible(timeout=15000)
        expect(self.page.get_by_role("button", name="Edit")).to_be_visible(timeout=15000)
        expect(self.page.get_by_role("button", name="Duplicate", exact=True)).to_be_visible(timeout=15000)
        expect(self.page.get_by_role("button", name="Delete")).to_be_visible(timeout=15000)

    def click_edit(self):
        self._click(self.page.get_by_role("button", name="Edit"))
        expect(self.page.get_by_role("button", name="Save")).to_be_visible(timeout=15000)

    def save_edit(self, name=None):
        # editing trigger words shows a warning that must be visible before saving
        expect(self.page.get_by_text("Changing trigger words may")).to_be_visible(timeout=5000)
        self._click(self.page.get_by_role("button", name="Save"))
        if name:
            expect(self.page.get_by_text(f'Changes to "{name}" have been successfully saved.')).to_be_visible(timeout=15000)
        expect(self.page.get_by_role("button", name="Edit")).to_be_visible(timeout=15000)
        expect(self.page.get_by_role("button", name="Save")).to_have_count(0, timeout=15000)

    def preview_card(self, name):
        """Open 'Preview card' from the card details, check the popup shows the card, then close it."""
        self._click(self.page.get_by_role("button", name="Preview card"))
        popup = self.page.locator("[role=dialog]").filter(has_text="AI LIVE COACH")
        expect(popup).to_be_visible(timeout=15000)
        expect(popup).to_contain_text(name)
        self.page.keyboard.press("Escape")
        expect(popup).to_have_count(0, timeout=10000)

    def click_duplicate(self):
        self._click(self.page.get_by_role("button", name="Duplicate", exact=True))
        expect(self._name_box()).to_be_visible(timeout=15000)
        expect(self.page.get_by_role("button", name="Create card")).to_be_visible(timeout=15000)

    def delete_current_card(self, name=None):
        self._click(self.page.get_by_role("button", name="Delete"))
        self._click(self.page.get_by_role("button", name="Yes, delete"))
        if name:
            # quote style / trailing text of the toast varies, so match name + "deleted" loosely
            toast = self.page.get_by_text(re.compile(rf"{re.escape(name)}\W{{0,3}}\s*deleted", re.I))
            try:
                expect(toast.first).to_be_visible(timeout=15000)
            except AssertionError:
                print(f"Delete toast for '{name}' not seen; relying on the not-listed check")
        expect(self.page.locator("dialog[open]")).to_have_count(0, timeout=15000)

    def close_card(self):
        self._click(self.page.get_by_role("button", name="Close", exact=True))
        expect(self.page.get_by_role("button", name="Edit")).to_have_count(0, timeout=15000)

    def _card_button(self, card_name):
        return self.page.get_by_role("button", name=card_name)

    def open_card(self, card_name):
        self._click(self.page.locator(self.CARD_LIST_DROPDOWN).first)
        self._click(self._card_button(card_name).first)
        expect(self.page.get_by_role("button", name="Edit")).to_be_visible(timeout=15000)

    def assert_card_listed(self, card_name):
        self._click(self.page.locator(self.CARD_LIST_DROPDOWN).first)
        expect(self._card_button(card_name).first).to_be_visible(timeout=10000)
        self.page.keyboard.press("Escape")

    def assert_card_not_listed(self, card_name):
        expect(self.page.get_by_text(card_name, exact=True)).to_have_count(0, timeout=15000)
