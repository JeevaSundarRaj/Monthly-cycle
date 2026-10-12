import os

import pytest
from playwright.sync_api import sync_playwright

from utils.call_recorder import write_csv, write_xlsx
from utils.result_logger import format_console_summary, record_report, write_results


def pytest_collection_modifyitems(items):
    """Inbox retention checks must run before any test that makes new calls."""
    inbox = [i for i in items if i.nodeid.startswith("tests/retention/test_inbox.py")]
    first_call = next((n for n, i in enumerate(items) if "calls" in i.keywords or
                       i.nodeid.startswith("tests/retention/test_calls.py")), None)
    if not inbox or first_call is None:
        return
    first = items[first_call]
    rest = [i for i in items if i not in inbox]
    items[:] = rest[:rest.index(first)] + inbox + rest[rest.index(first):]


def pytest_runtest_logreport(report):
    record_report(report)


def pytest_sessionfinish(session, exitstatus):
    print("\n" + format_console_summary())
    path, n = write_results()
    print(f"\nWrote {n} test results to {path}")
    count = write_csv("call_summary.csv")
    print(f"\nWrote {count} call entries to call_summary.csv")
    rows = write_xlsx("call_summary.xlsx")
    print(f"Wrote {rows} call rows to call_summary.xlsx")


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
