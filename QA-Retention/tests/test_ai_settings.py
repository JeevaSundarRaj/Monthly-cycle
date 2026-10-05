import json
import time

from pages.loginPage import LoginPage
from pages.aiSettingsPage import AiSettingsPage

GROUP_NAME = "test cc"


def _open_ai_settings(user_context):
    with open('data/userCred.json') as f:
        admin_user = json.load(f)["admin_user"]

    page = user_context.new_page()
    LoginPage(page).login(admin_user["username"], admin_user["password"],
                          url="https://dialpadbeta.com/login?c=/officesettings")
    ai = AiSettingsPage(page)
    ai.ensure_office_settings()
    return page, ai


class TestLiveCoachCard:

    def test_live_coach_card_crud(self, user_context):
        page = None
        suffix = str(int(time.time()))
        name = f"test LCC {suffix}"
        dup_name = f"{name} 2"
        try:
            page, ai = _open_ai_settings(user_context)
            ai.open_live_coach_cards()

            # create
            ai.start_create("lcc")
            ai.fill_name(name)
            ai.select_language("en")
            ai.fill_description("test")
            ai.fill_rep_response("test")
            ai.add_link("https://www.youtube.com", "youtube")
            ai.add_keywords("hi", "hello", "test")
            ai.assert_duplicate_keyword_rejected("test")
            ai.add_keywords("test2")
            ai.assign_group(GROUP_NAME)
            ai.create_card(name)

            # edit
            ai.click_edit()
            ai.assert_duplicate_keyword_rejected("hi")
            ai.add_keywords("one")
            ai.save_edit(name)

            # duplicate
            ai.click_duplicate()
            ai.fill_name(dup_name)
            ai.assign_group(GROUP_NAME)
            ai.select_language("en")
            ai.create_card(dup_name)
            ai.close_card()
            ai.assert_card_listed(dup_name)

            # delete both
            ai.open_card(dup_name)
            ai.delete_current_card(dup_name)
            ai.assert_card_not_listed(dup_name)
            ai.open_card(name)
            ai.delete_current_card(name)
            ai.assert_card_not_listed(name)
        finally:
            if page:
                page.close()


class TestCustomMoment:

    def test_custom_moment_crud(self, user_context):
        page = None
        suffix = str(int(time.time()))
        name = f"test cm {suffix}"
        dup_name = f"{name} 2"
        try:
            page, ai = _open_ai_settings(user_context)
            ai.open_custom_moments()

            # create
            ai.start_create("cm")
            ai.fill_name(name)
            ai.select_language("en")
            ai.fill_description("test")
            ai.add_keywords("hi", "hello")
            ai.assert_duplicate_keyword_rejected("hi")
            ai.add_keywords("hi2")
            ai.assign_group(GROUP_NAME)
            ai.create_card(name)

            # edit
            ai.click_edit()
            ai.assert_duplicate_keyword_rejected("hi")
            ai.add_keywords("okay")
            ai.save_edit(name)

            # duplicate
            ai.click_duplicate()
            ai.fill_name(dup_name)
            ai.fill_description("test duplicate")
            ai.assign_group(GROUP_NAME)
            ai.select_language("en")
            ai.create_card(dup_name)
            ai.close_card()
            ai.assert_card_listed(dup_name)

            # delete both
            ai.open_card(dup_name)
            ai.delete_current_card(dup_name)
            ai.assert_card_not_listed(dup_name)
            ai.open_card(name)
            ai.delete_current_card(name)
            ai.assert_card_not_listed(name)
        finally:
            if page:
                page.close()
