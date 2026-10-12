import re
import time

GEO_NAME = "test geo"
CC_NAME = "test cc for geo routing"
DEPT_NAME = "test dept"
# first 3 digits of the corona user's number (the UI requires E.164, so +1 is added); anything else falls back to the department
CORONA_PREFIX = "862"


def _assert_incoming_notification(page, routed_to):
    """Incoming-call toast must name the routed entity and say it was transferred from the geo router."""
    incoming = re.compile(rf"Incoming call to\s*{re.escape(routed_to)}", re.I)
    transferred = re.compile(rf"Transferred from\s*{re.escape(GEO_NAME)}", re.I)
    assert _wait_for_text(page, incoming), f"No 'Incoming call to {routed_to}' notification appeared"
    assert _wait_for_text(page, transferred), f"Call to '{routed_to}' was not marked 'Transferred from {GEO_NAME}'"


def _wait_for_text(page, pattern, timeout=30):
    """Poll every frame (the toast may not live in the main one) until `pattern` text is visible."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for frame in page.frames:
            try:
                if frame.get_by_text(pattern).first.is_visible():
                    return True
            except Exception:
                pass  # frame navigated/detached mid-poll
        time.sleep(0.5)
    print(f"Text {pattern.pattern!r} not found; frames: {[f.url for f in page.frames]}")
    return False
