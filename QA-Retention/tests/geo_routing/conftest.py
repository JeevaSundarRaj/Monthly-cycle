import json
import time
from types import SimpleNamespace

import pytest

from pages.contactCenterPage import ContactCenterPage
from pages.dpAppPage import DpAppPage
from pages.geoRoutingPage import GeoRoutingPage
from pages.loginPage import LoginPage
from tests.geo_routing.helpers import CC_NAME, CORONA_PREFIX, DEPT_NAME, GEO_NAME


@pytest.fixture
def geo_env(user_context):
    """Admin + corona (862) caller logged in, geo router created and pointing at CC_NAME; torn down afterwards.

    Tests that change the CC's business hours set `env.hours_changed = True` so the CC is put back to 24/7.
    """
    with open('data/userCred.json') as f:
        creds = json.load(f)
    admin = creds["admin_user"]
    external_user = creds.get("external_user") or creds.get("ExternalUser")
    assert external_user, "No external user credentials found in JSON"

    pages = [user_context.new_page(permissions=['camera', 'microphone']) for _ in range(2)]
    admin_page, ext_page = pages
    env = SimpleNamespace(admin_page=admin_page, ext_page=ext_page, hours_changed=False, geo=None, created=False)
    try:
        LoginPage(admin_page).login(admin["username"], admin.get("password", creds["common password"]))
        LoginPage(ext_page).login(external_user["username"], external_user["password"])
        time.sleep(5)

        env.admin_app = DpAppPage(admin_page)
        env.ext_app = DpAppPage(ext_page)
        for app in (env.admin_app, env.ext_app):
            _end_stale_call(app)  # a call left over from an aborted run keeps the CC 'Occupied'

        env.geo = GeoRoutingPage(admin_page)
        env.geo.open()
        env.geo.delete_existing(GEO_NAME)
        try:
            env.geo.create(GEO_NAME, f"+1{CORONA_PREFIX}", route_to=CC_NAME, fallback_to=DEPT_NAME)
        except Exception:
            admin_page.screenshot(path="dbg_geo.png")
            raise
        env.created = True
        env.geo_number = env.geo.read_number()
        print(f"Geo routing number: {env.geo_number}")
        yield env
    finally:
        try:
            if env.hours_changed:
                cc = ContactCenterPage(admin_page)
                cc.open_business_hours(CC_NAME)
                cc.set_always_open()
            if env.created:
                env.geo.open()
                env.geo.delete_existing(GEO_NAME)
        finally:
            for p in pages:
                p.close()


def _end_stale_call(app):
    end = app.page.locator('[data-name="Phone Hang Up"]').first
    try:
        end.wait_for(state="visible", timeout=5000)
    except Exception:
        return
    print("Ending stale call from a previous run")
    app.hang_up()
