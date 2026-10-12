import re
import time


from pages.contactCenterPage import ContactCenterPage
from tests.geo_routing.helpers import CC_NAME, _assert_incoming_notification, _wait_for_text

APP_URL = "https://dialpadbeta.com/app"
CLOSED_PHRASE = "no one is available"


def _to_app(env):
    env.admin_page.goto(APP_URL)
    time.sleep(5)


def _call_cc_while_24x7(env, cc):
    """Set the CC to 24/7 and check a corona caller reaches the agent, who hears audio played."""
    cc.open_business_hours(CC_NAME)
    cc.set_always_open()
    cc.reload()
    assert cc.is_always_open(), "'Always take calls (24/7)' did not persist after reload"

    _to_app(env)
    env.ext_app.make_call(env.geo_number)
    try:
        _assert_incoming_notification(env.admin_page, CC_NAME)
        env.admin_app.receive_call()
        env.ext_app.mute()  # only the shared mic -> admin side carries the audio
        env.admin_app.play_audio('data/testvoice.mp3')
    finally:
        env.ext_app.hang_up()


class TestGeoRoutingCc:

    def test_call_routing_cc_24x7(self, geo_env):
        """[Geo-Routing] With the CC set to 24/7, the routed call reaches the CC agent."""
        geo_env.hours_changed = True
        _call_cc_while_24x7(geo_env, ContactCenterPage(geo_env.admin_page))

    def test_ai_on_off_transcription(self, geo_env):
        """Route a call to the CC, toggle AI on then off while playing audio, and check the transcript follows."""
        env = geo_env
        cc = ContactCenterPage(env.admin_page)
        cc.open_business_hours(CC_NAME)
        cc.set_always_open()  # a CC left on 'specific hours' would be closed and never ring the agent
        _to_app(env)

        env.ext_app.make_call(env.geo_number)
        try:
            try:
                _assert_incoming_notification(env.admin_page, CC_NAME)
            except Exception:
                env.admin_page.screenshot(path="dbg_admin.png")
                env.ext_page.screenshot(path="dbg_ext.png")
                raise
            env.admin_app.receive_call()
            env.ext_app.mute()  # only the shared mic -> admin side carries the audio

            env.admin_app.enable_ai()
            assert env.admin_app.is_ai_on(), "AI did not turn on during the call"
            env.admin_app.play_audio('data/testvoice2.mp3')
            first = env.admin_app.wait_for_any_transcript(timeout=60)
            if not first:
                env.admin_page.screenshot(path="dbg_ai.png")
            assert first, "No transcript generated while AI was on"
            time.sleep(10)  # let in-flight transcription settle so the baseline is stable
            transcript_on = env.admin_app.read_transcript()

            env.admin_app.disable_ai()
            assert not env.admin_app.is_ai_on(), "AI did not turn off during the call"
            env.admin_app.play_audio('data/testvoice.mp3')
            time.sleep(5)
            transcript_off = env.admin_app.read_transcript()
            assert len(transcript_off) <= len(transcript_on), (
                f"Transcript kept growing after AI was turned off: {transcript_on!r} -> {transcript_off!r}"
            )
        finally:
            env.ext_app.hang_up()

    def test_business_hours_change(self, geo_env):
        """Corona caller -> CC twice: 24/7 connects to the agent (audio played), specific hours (closed) does not."""
        env = geo_env
        cc = ContactCenterPage(env.admin_page)
        env.hours_changed = True

        # ---- call 1: 24/7 -> automation user 1 gets the call ----
        _call_cc_while_24x7(env, cc)

        # ---- call 2: only during specific hours -> the call must not reach the agent ----
        cc.open_business_hours(CC_NAME)
        cc.set_specific_hours()
        cc.reload()
        assert cc.is_specific_hours(), "'Only during specific hours' did not persist after reload"

        _to_app(env)
        env.ext_app.make_call(env.geo_number)
        try:
            ringing = _wait_for_text(env.admin_page, re.compile(rf"Incoming call to\s*{re.escape(CC_NAME)}", re.I),
                                     timeout=15)
            assert not ringing, "Call rang the agent even though the CC is on 'Only during specific hours'"
        finally:
            env.ext_app.hang_up()

    def test_closed_hours_transcription(self, geo_env):
        """With 'Only during specific hours' and the CC closed, the corona caller's transcript says no one is available."""
        env = geo_env
        cc = ContactCenterPage(env.admin_page)
        env.hours_changed = True

        cc.open_business_hours(CC_NAME)
        cc.set_specific_hours()
        assert cc.is_specific_hours(), "'Only during specific hours' was not selected"

        _to_app(env)
        env.ext_app.make_call(env.geo_number)
        try:
            transcript = env.ext_app.wait_for_transcript_text(CLOSED_PHRASE, timeout=60)
            assert CLOSED_PHRASE in transcript.lower(), (
                f"Expected '{CLOSED_PHRASE}' in the caller's transcript (is the CC actually closed right now?), "
                f"got: {transcript!r}"
            )
        finally:
            env.ext_app.hang_up()
