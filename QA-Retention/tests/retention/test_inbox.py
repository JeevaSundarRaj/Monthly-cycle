import json
import time

import pytest

from pages.dpAppPage import DpAppPage, EntityNotAccessibleError, AllTabNotAvailableError
from pages.loginPage import LoginPage
from utils.retention_policy import is_remove_content_only


def _load_user_credentials():
    with open('data/userCred.json') as f:
        return json.load(f)


# Entities each operator can see, listed once overall: an entity another
# operator already covers is skipped (user142 is fully covered by user141 and
# user143; user147's CT 01/02 are covered by user143).
OPERATOR_PLAN = [
    ("retention.user141@gmail.com", [
        ("CT", "Dialpad Retention 02 CT 01"),
        ("CT", "Dialpad Retention 02 CT 02"),
        ("CC", "Dialpad Retention 02 CC 01"),
        ("Department", "Dialpad Retention 02 Dept 01"),
        ("Department", "Dialpad Retention 02 Dept 02"),
    ]),
    ("retention.user143@gmail.com", [
        ("CC", "Dialpad Retention 01 CC 01"),
        ("CT", "Dialpad Retention 01 CT 01"),
        ("CT", "Dialpad Retention 01 CT 02"),
        ("Department", "Dialpad Retention 01 Dept 02"),
    ]),
    ("retention.user145@gmail.com", [
        ("CT", "Dialpad Retention 03 CT 01"),
        ("CT", "Dialpad Retention 03 CT 02"),
        ("Department", "Dialpad Retention 03 Dept 02"),
    ]),
    ("retention.user146@gmail.com", [
        ("CC", "Dialpad Retention 03 CC 01"),
        ("Department", "Dialpad Retention 03 Dept 01"),
    ]),
    ("retention.user147@gmail.com", [
        ("Department", "Dialpad Retention 01 Dept 01"),
    ]),
]


def get_entity_policies(json_path):
    """Map each entity name to the policy option that governs it (first occurrence wins)."""
    with open(json_path, 'r') as f:
        data = json.load(f)

    policies = {}
    for policy_type in ("individual_policies", "inherited_policies"):
        for option_name, details in data.get(policy_type, {}).items():
            if not isinstance(details, dict):
                continue
            department = details.get("Department") or details.get("Departments") or {}
            for name in (
                department.get("Department Name"),
                (details.get("CC") or {}).get("CC Name"),
                (details.get("CT") or {}).get("Coaching team"),
            ):
                if name:
                    policies.setdefault(name, option_name)
    return policies


entity_policies = get_entity_policies('data/userCred.json')
# userCred.json lists this CT under Cleanup and Archive, but it is Remove Content only.
entity_policies["Dialpad Retention 03 CT 02"] = "Option 2: Remove Content"
operator_cases = [(operator, entities) for operator, entities in OPERATOR_PLAN]


def _verify_retention_for_operator(user_context, operator_username, entities):
    userCredentials = _load_user_credentials()

    operator_user_page = None

    try:
        operator_user_page = user_context.new_page(permissions=['camera', 'microphone'])

        operator_page = LoginPage(operator_user_page)
        operator_call_page = DpAppPage(operator_user_page)

        operator_page.login(operator_username, userCredentials["common password"])
        time.sleep(5)

        if operator_call_page.is_active_call():
            print("Active call detected after login, hanging up...")
            operator_call_page.hang_up()
            time.sleep(3)

        external_user = userCredentials.get("external_user") or userCredentials.get("ExternalUser")
        assert external_user, "No external user credentials found in JSON"
        corona_contact_name = external_user["displayName"]

        failures = []

        for entity_type, entity_name in entities:
            option_name = entity_policies.get(entity_name)
            assert option_name, f"No policy option found in userCred.json for '{entity_name}'"
            remove_content_only = is_remove_content_only(option_name)
            try:
                if entity_type == "CC":
                    operator_call_page.open_contact_center(entity_name)
                    operator_call_page.verify_retention_in_all_tab(entity_name, remove_content_only, corona_contact_name)
                elif entity_type == "CT":
                    operator_call_page.open_coaching_team(entity_name)
                    operator_call_page.verify_retention_in_recordings_tab(entity_name, remove_content_only)
                elif entity_type == "Department":
                    operator_call_page.open_department(entity_name)
                    operator_call_page.verify_retention_in_all_tab(entity_name, remove_content_only, corona_contact_name)
                else:
                    raise ValueError(f"Unknown entity_type: {entity_type}")
            except (EntityNotAccessibleError, AllTabNotAvailableError, AssertionError) as e:
                # OPERATOR_PLAN lists only entities the operator should reach, so
                # inaccessibility is a failure, not a skip. Keep checking the rest.
                print(f"FAILED {entity_type} '{entity_name}': {e}")
                failures.append(f"{entity_type} '{entity_name}': {e}")

        assert not failures, f"{len(failures)} retention check(s) failed for {operator_username}:\n" + "\n".join(failures)

    finally:
        if operator_user_page:
            operator_user_page.close()


class TestRetentionByOperator:

    @pytest.mark.parametrize("operator, entities", operator_cases)
    def test_check_inbox(self, user_context, operator, entities):
        entity_labels = ", ".join(f"{entity_type}:{entity_name}" for entity_type, entity_name in entities)
        print(
            f"\n--- Running retention check for Operator: '{operator}' ({entity_labels}) ---"
        )

        _verify_retention_for_operator(user_context, operator, entities)
