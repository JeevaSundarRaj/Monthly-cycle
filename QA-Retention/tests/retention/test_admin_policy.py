import pytest
import json

from playwright.sync_api import expect

from pages.loginPage import LoginPage
from pages.adminRetentionPage import AdminRetentionPage


def _login_as_admin(user_context):
    with open('data/userCred.json') as f:
        userCredentials = json.load(f)

    admin_user = userCredentials["admin_user"]
    targets = userCredentials["admin_retention_targets"]

    admin_page = user_context.new_page()
    login_page = LoginPage(admin_page)
    retention_page = AdminRetentionPage(admin_page)

    login_page.login(admin_user["username"], admin_user["password"], url="https://dialpadbeta.com/login")
    retention_page.go_to_admin_settings()

    return admin_page, retention_page, targets


def _clear_office_policy(retention_page):
    retention_page.open_office()
    retention_page.open_retention_policy_page()
    retention_page.clear_all_policies()


def _check_inherit_and_remove_options(retention_page, policy_option, days, exact):
    """Entity already has its own policy and the office has 36 days; exercise the remove dialog in both states.

    Own policy + office policy: 3 options (Cancel, Remove this policy and inherit, Remove all retention policies).
    Inherited only: 2 options (Cancel, Remove policy).
    """
    retention_page.verify_policy_set(days, policy_option)

    # own policy: Cancel keeps it
    retention_page.cancel_remove_policy()
    retention_page.verify_policy_set(days, policy_option)

    # own policy: Remove this policy and inherit -> office policy
    retention_page.remove_retention_policy(confirm_name="Remove this policy and inherit")
    retention_page.verify_policy_inherited(36)

    # inherited only: Cancel keeps the inherited policy
    retention_page.cancel_remove_policy()
    retention_page.verify_policy_inherited(36)

    # inherited only: Remove policy -> no policy at all
    retention_page.remove_retention_policy(confirm_name="Remove policy")
    retention_page.verify_no_policy()

    # own policy: Remove all retention policies -> no policy at all
    retention_page.set_retention_policy(policy_option=policy_option, days=days, exact=exact)
    retention_page.remove_retention_policy(confirm_name="Remove all retention policies")
    retention_page.verify_no_policy()

    # own policy again, fall back to inheriting, leaving the entity in the inherited state
    retention_page.set_retention_policy(policy_option=policy_option, days=days, exact=exact)
    retention_page.remove_retention_policy(confirm_name="Remove this policy and inherit")
    retention_page.verify_policy_inherited(36)


class TestAdminRetentionPolicySettings:

    def test_department_retention_policy(self, user_context):
        admin_page = None
        try:
            admin_page, retention_page, targets = _login_as_admin(user_context)

            retention_page.open_departments()
            retention_page.select_department(targets["department_name"])
            retention_page.open_advanced_settings()

            retention_page.set_retention_policy(days=3)
            retention_page.verify_policy_set(3, "Cleanup and archive")
            retention_page.update_retention_policy(policy_option="Remove Content", days=30, exact=True)
            retention_page.apply_policy()
            retention_page.verify_policy_set(30, "Remove Content")
            retention_page.remove_retention_policy()
        finally:
            if admin_page:
                admin_page.close()

    def test_contact_center_retention_policy(self, user_context):
        admin_page = None
        try:
            admin_page, retention_page, targets = _login_as_admin(user_context)

            retention_page.open_contact_centers()
            retention_page.select_contact_center(targets["cc_name"])
            retention_page.open_advanced_settings()

            retention_page.set_retention_policy(days=3)
            retention_page.verify_policy_set(3, "Cleanup and archive")
            retention_page.update_retention_policy(policy_option="Remove content and personally", days=15)
            retention_page.apply_policy()
            retention_page.verify_policy_set(15, "Remove content and personally")
            retention_page.remove_retention_policy()
        finally:
            if admin_page:
                admin_page.close()

    def test_coaching_team_retention_policy(self, user_context):
        admin_page = None
        try:
            admin_page, retention_page, targets = _login_as_admin(user_context)

            retention_page.open_coaching_teams()
            retention_page.select_coaching_team(targets["ct_name"])
            retention_page.open_advanced_settings()

            retention_page.set_retention_policy(policy_option="Remove content and personally", days=5)
            retention_page.verify_policy_set(5, "Remove content and personally")
            retention_page.update_retention_policy(policy_option="Cleanup and archive", days=2)
            retention_page.confirm_updated_policy()
            retention_page.verify_policy_set(2, "Cleanup and archive")
            retention_page.remove_retention_policy()
        finally:
            if admin_page:
                admin_page.close()

    def test_inherit_office_policy_for_department_and_ct(self, user_context):
        admin_page = None
        retention_page = None
        office_policy_set = False
        try:
            admin_page, retention_page, targets = _login_as_admin(user_context)

            entities = (
                (retention_page.open_departments, retention_page.select_department,
                 targets["department_name"], "Remove content and personally", 3, False),
                (retention_page.open_coaching_teams, retention_page.select_coaching_team,
                 targets["ct_name"], "Remove Content", 5, True),
            )

            def open_entity(open_list, select, name):
                open_list()
                select(name)
                retention_page.open_advanced_settings()

            # start clean: no policy on the department, CT or office
            for open_list, select, name, *_ in entities:
                open_entity(open_list, select, name)
                retention_page.clear_all_policies()
            _clear_office_policy(retention_page)

            # an entity only inherits after it had its own policy, so set that first
            for open_list, select, name, option, days, exact in entities:
                open_entity(open_list, select, name)
                retention_page.set_retention_policy(policy_option=option, days=days, exact=exact)

            retention_page.open_office()
            retention_page.open_retention_policy_page()
            retention_page.set_retention_policy(days=36)
            office_policy_set = True

            for open_list, select, name, option, days, exact in entities:
                open_entity(open_list, select, name)
                _check_inherit_and_remove_options(retention_page, option, days, exact)
        finally:
            if admin_page:
                if office_policy_set:
                    try:
                        _clear_office_policy(retention_page)
                    except Exception as e:
                        print(f"Office policy cleanup failed: {e}")
                admin_page.close()

    def test_remove_policy_from_retention_policy_page(self, user_context):
        admin_page = None
        try:
            admin_page, retention_page, _ = _login_as_admin(user_context)

            retention_page.open_office()
            retention_page.open_retention_policy_page()
            retention_page.set_retention_policy(days=36)
            retention_page.remove_retention_policy()
            expect(admin_page.get_by_role("button", name="Set Retention Policy")).to_be_visible(timeout=20000)
        finally:
            if admin_page:
                admin_page.close()
