import time

from playwright.sync_api import Page, expect


class AdminRetentionPage:
    def __init__(self, page: Page):
        self.page = page
        self._pending_days = None
        self._pending_policy_option = None

    def _click(self, locator, timeout=15000):
        locator.wait_for(state="attached", timeout=timeout)
        locator.wait_for(state="visible", timeout=timeout)
        locator.click(force=True)

    def _settle(self):
        time.sleep(3)  # policy summary panel reloads after a confirm action

    def _verify_toast(self, text, timeout=8000):
        expect(self.page.get_by_text(text)).to_be_visible(timeout=timeout)

    def go_to_admin_settings(self):
        self._click(self.page.get_by_role("link", name="Admin Settings"))

    def open_departments(self):
        self._click(self.page.get_by_role("link", name="Departments"))

    def open_contact_centers(self):
        self._click(self.page.get_by_role("link", name="Contact Centers"))

    def open_coaching_teams(self):
        self._click(self.page.get_by_role("link", name="Coaching Teams"))

    def select_department(self, department_name):
        self._click(self.page.get_by_text(department_name))

    def select_contact_center(self, cc_name):
        self._click(self.page.get_by_text(cc_name))

    def select_coaching_team(self, ct_name):
        self._click(self.page.get_by_text(ct_name))

    def open_advanced_settings(self):
        self._click(self.page.get_by_text("Advanced settings"))

    def clear_existing_policy(self, timeout=20000):
        """A policy left by an aborted run hides 'Set Retention Policy'; remove it so the test starts clean."""
        set_btn = self.page.get_by_role("button", name="Set Retention Policy")
        remove_btn = self.page.get_by_role("button", name="Remove Retention Policy")
        set_btn.or_(remove_btn).first.wait_for(state="attached", timeout=timeout)
        if remove_btn.count():
            print("Found a leftover retention policy; removing it before the test")
            self.remove_retention_policy()
            set_btn.wait_for(state="attached", timeout=timeout)

    def set_retention_policy(self, policy_option=None, days=None, exact=False):
        self.clear_existing_policy()
        self._click(self.page.get_by_role("button", name="Set Retention Policy"))
        if policy_option:
            radio = self.page.get_by_role("radio", name=policy_option, exact=exact)
            radio.wait_for(state="visible", timeout=15000)
            radio.check(force=True)
        if days is not None:
            days_field = self.page.get_by_role("spinbutton", name="Days:")
            days_field.wait_for(state="visible", timeout=15000)
            days_field.fill(str(days))
        self._click(self.page.get_by_role("button", name="Save Policy"))
        confirm = self.page.get_by_role("button", name="Set Policy")
        try:
            confirm.wait_for(state="visible", timeout=4000)
            self._click(confirm)
        except Exception:
            print("No 'Set Policy' confirmation shown; checking whether the policy saved directly")
        try:
            self._verify_toast("Retention policy saved")
        except AssertionError:
            # the toast is short-lived; the summary check below is the real assertion
            print("'Retention policy saved' toast not seen; verifying the policy summary instead")
        self._settle()
        self._pending_days = days
        self._pending_policy_option = policy_option
        self._verify_pending_policy()

    def update_retention_policy(self, policy_option=None, days=None, exact=False):
        self._click(self.page.get_by_role("button", name="Update Retention Policy"))
        if policy_option:
            radio = self.page.get_by_role("radio", name=policy_option, exact=exact)
            radio.wait_for(state="visible", timeout=15000)
            radio.check(force=True)
        if days is not None:
            days_field = self.page.get_by_role("spinbutton", name="Days:")
            days_field.wait_for(state="visible", timeout=15000)
            days_field.fill(str(days))
        self._click(self.page.get_by_role("button", name="Save Policy"))
        # remember what was entered so apply_policy/confirm_updated_policy can
        # verify the UI reflects it once the summary panel reloads
        if days is not None:
            self._pending_days = days
        if policy_option:
            self._pending_policy_option = policy_option

    def _verify_pending_policy(self, timeout=20000):
        if self._pending_days is not None:
            self.verify_policy_set(self._pending_days, self._pending_policy_option, timeout=timeout)

    def apply_policy(self):
        self._click(self.page.get_by_role("button", name="Apply Policy"))
        self._verify_toast("Retention policy saved")
        self._settle()
        self._verify_pending_policy()

    def confirm_updated_policy(self):
        self._click(self.page.get_by_role("button", name="Update Policy"))
        self._verify_toast("Retention policy saved")
        self._settle()
        self._verify_pending_policy()

    def verify_retention_days(self, days, timeout=20000):
        expect(self.page.get_by_text(f"Retention Days: {days} days")).to_be_visible(timeout=timeout)

    def verify_policy_set(self, days, policy_option=None, timeout=20000):
        expect(self.page.get_by_text("Policy Set:")).to_be_visible(timeout=timeout)
        if policy_option:
            expect(self.page.get_by_text(policy_option).first).to_be_visible(timeout=timeout)
        self.verify_retention_days(days, timeout=timeout)

    def remove_retention_policy(self):
        confirm = self.page.get_by_role("button", name="Remove policy")
        for attempt in range(3):
            # the summary panel can re-render under the first click, so retry until the dialog opens
            self._click(self.page.get_by_role("button", name="Remove Retention Policy"))
            try:
                confirm.wait_for(state="visible", timeout=5000)
                break
            except Exception:
                if attempt == 2:
                    raise
        self._click(confirm)
        self._verify_toast("Retention policy removed")
        self._settle()
        self._pending_days = None
        self._pending_policy_option = None
