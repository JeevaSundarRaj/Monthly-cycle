import pytest
import json
import time

from pages.dpAppPage import DpAppPage
from pages.geoRoutingPage import GeoRoutingPage
from pages.loginPage import LoginPage
from tests.geo_routing.helpers import (
    CC_NAME, CORONA_PREFIX, DEPT_NAME, GEO_NAME, _assert_incoming_notification,
)

class TestGeoRouting:

    def test_geo_routing(self, user_context):
        with open('data/userCred.json') as f:
            creds = json.load(f)

        admin = creds["admin_user"]
        external_user = creds.get("external_user") or creds.get("ExternalUser")
        user2 = creds.get("automation_user2")
        assert external_user, "No external user credentials found in JSON"
        assert user2 and user2.get("username"), "Add 'automation_user2' (username[, password]) to data/userCred.json"

        admin_page = ext_page = user2_page = None
        geo = None
        created = False
        try:
            admin_page = user_context.new_page(permissions=['camera', 'microphone'])
            ext_page = user_context.new_page(permissions=['camera', 'microphone'])
            user2_page = user_context.new_page(permissions=['camera', 'microphone'])

            LoginPage(admin_page).login(admin["username"], admin.get("password", creds["common password"]))
            LoginPage(ext_page).login(external_user["username"], external_user["password"])
            LoginPage(user2_page).login(user2["username"], user2.get("password", creds["common password"]))
            time.sleep(5)

            admin_app = DpAppPage(admin_page)
            ext_app = DpAppPage(ext_page)
            user2_app = DpAppPage(user2_page)

            if admin_app.is_active_call():
                admin_app.hang_up()

            # ---- create the geo router ----
            geo = GeoRoutingPage(admin_page)
            geo.open()
            geo.delete_existing(GEO_NAME)
            geo.create(GEO_NAME, f"+1{CORONA_PREFIX}", route_to=CC_NAME, fallback_to=DEPT_NAME)
            created = True
            geo_number = geo.read_number()
            print(f"Geo routing number: {geo_number}")

            # back to the app so incoming calls ring on the admin page
            admin_page.goto("https://dialpadbeta.com/app")
            time.sleep(5)

            # ---- corona user (862) -> CC_NAME ----
            ext_app.make_call(geo_number)
            try:
                _assert_incoming_notification(admin_page, CC_NAME)
            except Exception:
                admin_page.screenshot(path="dbg_admin.png")
                ext_page.screenshot(path="dbg_ext.png")
                seen = admin_page.locator("[class*='notification']").all_inner_texts()
                print(f"Admin notification-like elements: {seen!r}")
                print(f"Admin page URL: {admin_page.url}")
                raise
            finally:
                ext_app.hang_up()  # caller cancels, even if the assertion failed

            # ---- automation user2 -> test dept (fallback) ----
            user2_app.make_call(geo_number)
            try:
                _assert_incoming_notification(admin_page, DEPT_NAME)
            finally:
                user2_app.hang_up()
        finally:
            try:
                if created and admin_page:
                    geo.open()
                    geo.delete_existing(GEO_NAME)
            finally:
                for p in (admin_page, ext_page, user2_page):
                    if p:
                        p.close()


class TestGeoRoutingNumber:

    def test_add_local_number(self, user_context):
        """[Geo-Routing] A new router's first step is adding a local number."""
        admin = json.load(open('data/userCred.json'))["admin_user"]
        creds = json.load(open('data/userCred.json'))
        page = geo = None
        created = False
        try:
            page = user_context.new_page()
            LoginPage(page).login(admin["username"], admin.get("password", creds["common password"]))
            time.sleep(5)
            geo = GeoRoutingPage(page)
            geo.open()
            geo.delete_existing(GEO_NAME)
            geo.create_router(GEO_NAME)
            created = True
            geo.add_number()
            number = geo.read_number()
            print(f"Added local number: {number}")
            assert len(number) >= 10, f"Unexpected number {number!r}"
        finally:
            try:
                if created and page:
                    geo.open()
                    geo.delete_existing(GEO_NAME)
            finally:
                if page:
                    page.close()
