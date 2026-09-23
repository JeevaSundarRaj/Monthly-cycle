import json

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
