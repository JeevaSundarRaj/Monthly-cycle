import os

import pytest
from playwright.sync_api import sync_playwright

from utils.call_recorder import write_csv


def pytest_sessionfinish(session, exitstatus):
    count = write_csv("call_summary.csv")
    print(f"\nWrote {count} call entries to call_summary.csv")


@pytest.fixture(scope='function')
def user_context():
    is_ci = os.getenv('CI') == 'true'

    with sync_playwright() as p:
        launch_options = {"channel": "chrome"}

        if is_ci:
            launch_options["args"] = [
                "--headless=new",
                "--use-fake-device-for-media-stream",
                "--use-fake-ui-for-media-stream",
                "--no-sandbox",
            ]
        else:
            launch_options["headless"] = False

        browser = p.chromium.launch(**launch_options)
        yield browser
        browser.close()
