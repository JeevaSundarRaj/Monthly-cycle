from playwright.sync_api import Page
import os
import json
import re
import time
import pyperclipimg as pci
import sounddevice as sd
import soundfile as sf


class EntityNotAccessibleError(Exception):
    """Raised when the operator does not have visibility into the requested entity."""


class AllTabNotAvailableError(Exception):
    """Raised when the 'All' tab is not available for the current operator (e.g. non-admin)."""


class DpAppPage:
    def __init__(self, page: Page):
        self.page = page
        locators_path = os.path.join(os.path.dirname(__file__), 'elements', 'locators.json')
        with open(locators_path) as p:
            self.locators = json.load(p)

    def make_call(self, phonenumber):
        self.page.locator(self.locators['makeCallButton']).click()
        self.page.locator(self.locators['callSearch']).fill(str(phonenumber))
        self.page.locator(self.locators['callButton']).click()

    def hang_up(self):
        self.page.wait_for_selector('[data-name="Phone Hang Up"]',
                                    state='attached',
                                    timeout=10000)
        self.page.wait_for_selector('[data-name="Phone Hang Up"]',
                                    state='visible',
                                    timeout=10000)
        self.page.click('[data-name = "Phone Hang Up"]', force=True)
        print('Phone hanged up successfully')
        time.sleep(12)

    def receive_call(self):
        button = self.page.wait_for_selector('text="Accept"',
                                             state='visible',
                                             timeout=25000)
        button.click()
        print('Clicked Answer button')
        time.sleep(5)

    def decline_call(self):
        self.page.wait_for_selector('text="Decline"', state='visible', timeout=20000).click()

    def is_active_call(self):
        try:
            locator = self.page.locator(self.locators['activeCall'])
            locator.wait_for(state="visible", timeout=5000)  # wait up to 5 seconds for it to be visible
            return locator.is_visible()  # returns True if visible
        except Exception:
            return False

    def mute(self, retries=3, timeout=15000):
        last_error = None
        for attempt in range(retries):
            try:
                self.page.wait_for_selector('text="Mute"', state='attached', timeout=timeout)
                self.page.wait_for_selector('text="Mute"', state='visible', timeout=timeout)
                self.page.click('text="Mute"', force=True)
                print(" User is in Mute State")
                return
            except Exception as e:
                last_error = e
                print(f"mute() attempt {attempt + 1}/{retries} failed, retrying...")
        raise last_error

    def _dismiss_blocking_modal(self, timeout=2000):
        modal = self.page.locator("[data-qa='dt-modal']").first
        try:
            modal.wait_for(state="visible", timeout=timeout)
        except Exception:
            return

        self.page.keyboard.press("Escape")
        try:
            modal.wait_for(state="hidden", timeout=5000)
            return
        except Exception:
            pass

        # Some modals ignore Escape and require an explicit close/dismiss
        # click instead.
        close_button = modal.get_by_role("button", name=re.compile("close|dismiss|cancel|got it|ok", re.I)).first
        try:
            close_button.click(timeout=3000)
            modal.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

    def _click_with_modal_dismiss(self, locator, attempts=3, timeout=10000):
        for attempt in range(attempts):
            try:
                locator.click(timeout=timeout)
                return
            except Exception:
                if attempt == attempts - 1:
                    raise
                self._dismiss_blocking_modal()

    def new_call_as(self):
        self.page.locator(self.locators['newCallAsButton']).click()

    def send_message(self, message):
        self.page.get_by_placeholder(self.locators['messageInput']).fill(message)
        time.sleep(1000)
        self.page.locator(self.locators['messageSendButton']).click()

    def makeOutboundAs(self, phoneNumber, departmentName):
        self.page.locator(self.locators['makeCallButton']).click()
        self.page.locator(self.locators['newCallAsButton']).click()
        # Format the XPath with the department name
        call_as_xpath = self.locators['callAs'].format(departmentName)
        self.page.locator(call_as_xpath).click()
        # Optionally, continue with the call flow:
        self.page.locator(self.locators['callSearch']).fill(str(phoneNumber))
        self.page.locator(self.locators['callButton']).click()

    def sendMessage(self):
        self.page.locator(self.locators['messageInput']).fill("Test message")
        self.page.locator(self.locators['messageSendButton']).click()

    def send_image_by_upload(self):
        self.page.locator(self.locators['messageInput']).click()
        file_input = self.locator('input[type="file"]')
        file_input.set_input_files("tests/data/sample.png")
        self.click(self.locators['messageSendButton']).click()

    def send_image_by_clipboard_paste(self):

        pci.copy("data/test_image.jpg")

        self.page.locator(self.locators['messageInput']).click()

        self.page.keyboard.press("Meta+V")
        time.sleep(3)

        self.page.locator(self.locators['messageSendButton']).click()

        time.sleep(3)  # wait for UI update

    def play_audio(self, filename):
        data, samplerate = sf.read(filename)
        print(f"Playing audio: {filename}")
        sd.play(data, samplerate)
        sd.wait()
        print("Playback finished.")

    def _scroll_to_and_click_link(self, name, timeout=20000):
        # Departments/Coaching Teams children render asynchronously after the
        # section is expanded, so wait directly on the target rather than
        # polling via an unrelated scroll container.
        target = self.page.get_by_role("link", name=re.compile(re.escape(name))).first
        try:
            target.wait_for(state="visible", timeout=timeout)
        except Exception:
            raise EntityNotAccessibleError(
                f"'{name}' was not found in the list — operator is not part of it"
            )

        target.scroll_into_view_if_needed(timeout=15000)
        self._click_with_modal_dismiss(target)

    def open_contact_center(self, cc_name, timeout=20000):
        self._dismiss_blocking_modal()
        self._click_with_modal_dismiss(self.page.get_by_role("link", name=re.compile(r"Contact Centers")))

        # The "My contact centers" list is a management table, not a link
        # list — rows are plain text, so they must be matched by text. A
        # plain page-wide text match is ambiguous: if this CC has ever
        # appeared in "Recents" (e.g. from a prior test call routed through
        # it), that leftover conversation row also matches the same text and
        # can win instead of the actual management-table row. Scope the
        # match to the table's title cell to avoid picking the wrong one.
        target = self.page.locator("[data-qa='dt-item-layout-title-wrapper']").get_by_text(cc_name, exact=True).first
        try:
            target.wait_for(state="visible", timeout=timeout)
        except Exception:
            raise EntityNotAccessibleError(
                f"'{cc_name}' was not found in the Contact Centers list — operator is not part of it"
            )

        target.scroll_into_view_if_needed(timeout=15000)
        self._click_with_modal_dismiss(target)
        time.sleep(2)

    def _expand_section(self, section_name):
        # The sidebar header toggles; the section may already be open (or
        # start collapsed), so read aria-expanded before clicking.
        header = self.page.get_by_role("button", name=section_name, exact=True)
        expanded = header.get_attribute("aria-expanded")
        if expanded != "true":
            self._click_with_modal_dismiss(header)

    def open_coaching_team(self, ct_name):
        self._dismiss_blocking_modal()
        self._expand_section("Coaching Teams")
        self._scroll_to_and_click_link(ct_name)
        time.sleep(2)

    def open_department(self, department_name):
        self._dismiss_blocking_modal()
        self._expand_section("Departments")
        self._scroll_to_and_click_link(department_name)
        time.sleep(2)

    def _find_and_click_row(self, target, scroll_steps=30):
        """Scroll the current list until `target` is visible, then click it. Returns False if never found."""
        # Scroll the main pane, not the sidebar (which also uses dp-general-row).
        anchor_row = self.page.locator("#contact-list tr").first
        try:
            anchor_row.wait_for(state="visible", timeout=15000)
            anchor_row.hover()
        except Exception:
            pass

        for _ in range(scroll_steps):
            if target.count() > 0 and target.is_visible():
                break
            self.page.mouse.wheel(0, 400)
            time.sleep(0.3)

        if target.count() == 0 or not target.is_visible():
            return False

        target.scroll_into_view_if_needed(timeout=15000)
        self._click_with_modal_dismiss(target)
        time.sleep(2)
        return True

    def _all_tab(self):
        return self.page.get_by_role("tab", name=re.compile(r"^All\s*$"))

    def _voicemail_tab(self):
        return self.page.get_by_role("tab", name=re.compile(r"^Voicemails?\s*$"))

    def _open_conversation_row(self, contact_name, entity_name):
        """Open the contact's conversation.

        Returns "contact" if the corona contact was opened, "first" if only the
        first All-tab conversation could be opened, or None if nothing opened.

        Lookup order (first corona match wins, there can be several):
          1. the contact in the All tab
          2. the contact in the Voicemail tab
          3. the first conversation in the All tab
        """
        # Scope to the main pane: the sidebar Recents list can also contain this contact.
        contact_row = self.page.locator("#center-column").get_by_text(contact_name).first
        if self._find_and_click_row(contact_row):
            return "contact"

        voicemail_tab = self._voicemail_tab()
        if voicemail_tab.count() > 0 and voicemail_tab.first.is_visible():
            voicemail_tab.first.click()
            time.sleep(2)
            if self._find_and_click_row(contact_row, scroll_steps=5):
                print(f"'{contact_name}' not in All tab for '{entity_name}', used Voicemail tab")
                return "contact"

        self._all_tab().click()
        time.sleep(2)
        first_row = self.page.locator("#contact-list tr").first
        if self._find_and_click_row(first_row, scroll_steps=1):
            print(f"'{contact_name}' not found for '{entity_name}', used the first conversation in the All tab")
            return "first"

        return None

    def verify_retention_in_all_tab(self, entity_name, remove_content_only, contact_name):
        all_tab = self._all_tab()
        try:
            all_tab.wait_for(state="visible", timeout=5000)
        except Exception:
            raise AllTabNotAvailableError(
                f"'All' tab is not available for '{entity_name}' — operator is likely non-admin"
            )
        all_tab.click()
        time.sleep(2)

        opened = self._open_conversation_row(contact_name, entity_name)
        is_empty = opened is not None and self.page.locator(self.locators['conversationEmptyState']).is_visible()

        # A non-corona first row only tells us something when it is an empty
        # "Your conversation with X will appear here" pane (and the policy
        # purges everything). Otherwise its content is unrelated to the test
        # calls, so fall back to the Recordings tab.
        if opened is None or (opened == "first" and (remove_content_only or not is_empty)):
            print(f"No usable corona conversation for '{entity_name}', checking the Recordings tab")
            self.verify_retention_in_recordings_tab(entity_name, remove_content_only)
            return

        if remove_content_only:
            assert not is_empty, (
                f"Expected call titles to remain for '{entity_name}' under the Remove Content policy, "
                f"but the conversation list is completely empty"
            )
            # Call-title rows render empty .d-ws-pre-wrap nodes; only real text is content.
            content_items = self.page.locator(self.locators['feedItemText'])
            content_count = sum(
                1 for i in range(content_items.count()) if content_items.nth(i).inner_text().strip()
            )
            assert content_count == 0, (
                f"Expected no message content for '{entity_name}' under the Remove Content policy, "
                f"but found {content_count} content item(s)"
            )
            print(f"All-tab check passed for '{entity_name}': titles present, no message content (Remove Content)")
        else:
            assert is_empty, (
                f"Expected no information in the 'All' tab for '{entity_name}', "
                f"but the conversation list still has entries"
            )
            print(f"All-tab check passed for '{entity_name}': no information present")

    def verify_retention_in_recordings_tab(self, entity_name, remove_content_only):
        self.page.get_by_role("tab", name="Recordings").click()
        time.sleep(2)

        no_recordings = self.page.get_by_text("You have no recordings", exact=False)

        if remove_content_only:
            assert not no_recordings.is_visible(), (
                f"Expected a recording to remain for '{entity_name}' under the Remove Content policy, "
                f"but the recordings list is empty"
            )

            # Each recording row shows its deleted notice inline.
            deleted_notice = self.page.get_by_text("This recording has been deleted.").first
            assert deleted_notice.is_visible(), (
                f"Expected the recording for '{entity_name}' to show as deleted under the Remove Content policy, "
                f"but no 'This recording has been deleted.' notice is visible"
            )
            print(f"Recordings-tab check passed for '{entity_name}': recording shown as deleted (Remove Content)")
        else:
            assert no_recordings.is_visible(), (
                f"Expected no recordings for '{entity_name}', "
                f"but the recordings list still has entries"
            )
            print(f"Recordings-tab check passed for '{entity_name}': no recordings present")
