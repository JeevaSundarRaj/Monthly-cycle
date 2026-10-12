import time

import pytest

from pages.aiSettingsPage import AiSettingsPage
from pages.loginPage import LoginPage
from utils.creds import load_creds

GROUP_NAME = "test cc"

# lcc = Live Coach Card; cm = Custom Moment
CARD_TYPES = {
    "lcc": {"label": "Live coach card", "prefix": "test LCC", "open": "open_live_coach_cards",
            "keywords": ("hi", "hello", "test"), "dup_keyword": "test", "extra_keyword": "test2",
            "edit_keyword": "one", "template_keyword": "tmplkw"},
    "cm": {"label": "Custom moment card", "prefix": "test cm", "open": "open_custom_moments",
           "keywords": ("hi", "hello"), "dup_keyword": "hi", "extra_keyword": "hi2",
           "edit_keyword": "okay", "template_keyword": "tmplkw"},
}
card_types = pytest.mark.parametrize("card_type", list(CARD_TYPES))


def _open_ai_settings(user_context, card_type):
    admin_user = load_creds()["admin_user"]
    page = user_context.new_page()
    LoginPage(page).login(admin_user["username"], admin_user["password"],
                          url="https://dialpadbeta.com/login?c=/officesettings")
    ai = AiSettingsPage(page)
    ai.ensure_office_settings()
    getattr(ai, CARD_TYPES[card_type]["open"])()
    return page, ai


def _create_from_scratch(ai, card_type, name):
    cfg = CARD_TYPES[card_type]
    ai.start_create(card_type)
    ai.fill_name(name)
    ai.select_language("en")
    ai.fill_description("test")
    if card_type == "lcc":
        ai.fill_rep_response("test")
        ai.add_link("https://www.youtube.com", "youtube")
    ai.add_keywords(*cfg["keywords"])
    ai.assert_duplicate_keyword_rejected(cfg["dup_keyword"])
    ai.add_keywords(cfg["extra_keyword"])
    ai.assign_group(GROUP_NAME)
    ai.create_card(name)


def _create_from_template(ai, card_type, name):
    """Template prefills some fields/keywords, so only name, a new keyword and group are set."""
    cfg = CARD_TYPES[card_type]
    ai.start_create(card_type, from_template=True)
    ai.fill_name(name)
    ai.select_language("en")
    ai.add_keywords(cfg["template_keyword"])
    ai.assert_duplicate_keyword_rejected(cfg["template_keyword"])
    ai.assign_group(GROUP_NAME)
    ai.create_card(name)


def _delete_current(ai, name):
    ai.delete_current_card(name)
    ai.assert_card_not_listed(name)


class TestAiCards:

    @card_types
    def test_create_from_scratch(self, user_context, card_type):
        """[CM & LCC] Verify creating a new card from scratch."""
        name = f"{CARD_TYPES[card_type]['prefix']} {int(time.time())}"
        page = None
        try:
            page, ai = _open_ai_settings(user_context, card_type)
            _create_from_scratch(ai, card_type, name)
            _delete_current(ai, name)
        finally:
            if page:
                page.close()

    @card_types
    def test_edit_and_delete(self, user_context, card_type):
        """[CM & LCC] Verify options to Edit and Delete the card."""
        cfg = CARD_TYPES[card_type]
        name = f"{cfg['prefix']} {int(time.time())}"
        page = None
        try:
            page, ai = _open_ai_settings(user_context, card_type)
            _create_from_scratch(ai, card_type, name)
            ai.click_edit()
            ai.assert_duplicate_keyword_rejected("hi")
            ai.add_keywords(cfg["edit_keyword"])
            ai.save_edit(name)
            _delete_current(ai, name)
        finally:
            if page:
                page.close()

    @card_types
    def test_duplicate_and_delete(self, user_context, card_type):
        """Duplicate a card, then delete both copies."""
        name = f"{CARD_TYPES[card_type]['prefix']} {int(time.time())}"
        dup_name = f"{name} 2"
        page = None
        try:
            page, ai = _open_ai_settings(user_context, card_type)
            _create_from_scratch(ai, card_type, name)
            ai.click_duplicate()
            ai.fill_name(dup_name)
            ai.assign_group(GROUP_NAME)
            ai.select_language("en")
            ai.create_card(dup_name)
            ai.close_card()
            ai.assert_card_listed(dup_name)
            ai.open_card(dup_name)
            _delete_current(ai, dup_name)
            ai.open_card(name)
            _delete_current(ai, name)
        finally:
            if page:
                page.close()


class TestAiCardsFromTemplate:

    @card_types
    def test_create_from_template(self, user_context, card_type):
        """[CM & LCC] Verify creating a new card from a template."""
        name = f"{CARD_TYPES[card_type]['prefix']} tmpl {int(time.time())}"
        page = None
        try:
            page, ai = _open_ai_settings(user_context, card_type)
            _create_from_template(ai, card_type, name)
            _delete_current(ai, name)
        finally:
            if page:
                page.close()

    @card_types
    def test_template_card_edit_delete(self, user_context, card_type):
        """[CM & LCC] Verify Edit and Delete for a card created from a template."""
        cfg = CARD_TYPES[card_type]
        name = f"{cfg['prefix']} tmpl {int(time.time())}"
        page = None
        try:
            page, ai = _open_ai_settings(user_context, card_type)
            _create_from_template(ai, card_type, name)
            ai.click_edit()
            ai.add_keywords(cfg["edit_keyword"])
            ai.save_edit(name)
            _delete_current(ai, name)
        finally:
            if page:
                page.close()


class TestAiCardPreview:

    def test_live_coach_card_preview(self, user_context):
        """[LCC] After creating a card, Preview card shows it."""
        name = f"{CARD_TYPES['lcc']['prefix']} preview {int(time.time())}"
        page = None
        try:
            page, ai = _open_ai_settings(user_context, "lcc")
            _create_from_scratch(ai, "lcc", name)
            ai.preview_card(name)
            _delete_current(ai, name)
        finally:
            if page:
                page.close()
