from playwright.sync_api import Page
import os
import json
import time
import pyperclipimg as pci
import sounddevice as sd
import soundfile as sf


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
        except Exception:
            pass

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

    def verify_inbox_before_call(self, contact_name, remove_content_only):
        contact_locator = self.page.locator(self.locators['contactRow'].format(contact_name))

        self._dismiss_blocking_modal()

        anchor_row = self.page.locator("[data-qa='dp-general-row']").first
        anchor_row.wait_for(state="visible", timeout=15000)
        anchor_row.hover()
        for _ in range(30):
            if contact_locator.count() > 0 and contact_locator.first.is_visible():
                break
            self.page.mouse.wheel(0, 400)
            time.sleep(0.3)

        contact_locator.first.scroll_into_view_if_needed(timeout=15000)
        contact_locator.first.click()
        time.sleep(2)

        is_empty = self.page.locator(self.locators['conversationEmptyState']).is_visible()

        if remove_content_only:
            assert not is_empty, (
                f"Expected call titles to remain for '{contact_name}' under the Remove Content policy, "
                f"but the conversation is completely empty"
            )
            content_count = self.page.locator(self.locators['feedItemText']).count()
            assert content_count == 0, (
                f"Expected no message content for '{contact_name}' under the Remove Content policy, "
                f"but found {content_count} content item(s)"
            )
            print(f"Inbox check passed for '{contact_name}': titles present, no message content (Remove Content)")
        else:
            assert is_empty, (
                f"Expected no information in the inbox for '{contact_name}', "
                f"but the conversation still has entries"
            )
            print(f"Inbox check passed for '{contact_name}': no information present")
