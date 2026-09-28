import json
import time

import pytest

from pages.dpAppPage import DpAppPage, EntityNotAccessibleError, AllTabNotAvailableError
from pages.loginPage import LoginPage
from utils.retention_policy import is_remove_content_only


def _load_user_credentials():
    with open('data/userCred.json') as f:
        return json.load(f)


def get_operator_cases(json_path):
    """Group CC/CT/Department entities by the operator who can see them.

    Several entities in a policy option share the same operator (e.g. the
    department operator is often also the CT trainee), so grouping lets a
    single login check every entity that operator has access to instead of
    logging in once per entity.
    """
    with open(json_path, 'r') as f:
        data = json.load(f)

    cases = []

    for policy_type in ("individual_policies", "inherited_policies"):
        for option_name, policy_details in data.get(policy_type, {}).items():
            if not isinstance(policy_details, dict):
                continue

            entities_by_operator = {}

            department_info = policy_details.get("Department") or policy_details.get("Departments")
            if department_info:
                operator = department_info.get("Dep operator")
                name = department_info.get("Department Name")
                if operator and name:
                    entities_by_operator.setdefault(operator, []).append(("Department", name))

            cc_info = policy_details.get("CC")
            if cc_info:
                operator = cc_info.get("CC Agent")
                name = cc_info.get("CC Name")
                if operator and name:
                    entities_by_operator.setdefault(operator, []).append(("CC", name))

            ct_info = policy_details.get("CT")
            if ct_info:
                operator = ct_info.get("Trainee")
                name = ct_info.get("Coaching team")
                if operator and name:
                    entities_by_operator.setdefault(operator, []).append(("CT", name))

            for operator, entities in entities_by_operator.items():
                cases.append((policy_type, option_name, operator, entities))

    return cases


operator_cases = get_operator_cases('data/userCred.json')


def _verify_retention_for_operator(user_context, operator_username, option_name, entities):
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

        remove_content_only = is_remove_content_only(option_name)

        external_user = userCredentials.get("external_user") or userCredentials.get("ExternalUser")
        assert external_user, "No external user credentials found in JSON"
        corona_contact_name = external_user["displayName"]

        skipped_reasons = []
        checked_any = False

        for entity_type, entity_name in entities:
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
                checked_any = True
            except (EntityNotAccessibleError, AllTabNotAvailableError) as e:
                print(f"Skipping {entity_type} '{entity_name}': {e}")
                skipped_reasons.append(str(e))

        if not checked_any:
            pytest.skip("; ".join(skipped_reasons) or "No entities were accessible for this operator")

    finally:
        if operator_user_page:
            operator_user_page.close()


class TestRetentionByOperator:

    @pytest.mark.parametrize("policy_type, option_name, operator, entities", operator_cases)
    def test_retention_by_operator(self, user_context, policy_type, option_name, operator, entities):
        entity_labels = ", ".join(f"{entity_type}:{entity_name}" for entity_type, entity_name in entities)
        print(
            f"\n--- Running retention check for Policy Type: '{policy_type}', "
            f"Option: '{option_name}', Operator: '{operator}' ({entity_labels}) ---"
        )

        _verify_retention_for_operator(user_context, operator, option_name, entities)
