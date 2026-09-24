import json
import time

import pytest

from pages.dpAppPage import DpAppPage
from pages.loginPage import LoginPage
from utils.retention_policy import is_remove_content_only


def _load_user_credentials():
    with open('data/userCred.json') as f:
        return json.load(f)


def get_ct_cases(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    ct_list = []

    for policy_type in ("individual_policies", "inherited_policies"):
        for option_name, policy_details in data.get(policy_type, {}).items():
            if isinstance(policy_details, dict) and "CT" in policy_details:
                ct_list.append((policy_type, option_name, policy_details["CT"]))

    return ct_list


def get_cc_cases(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    cc_list = []

    for policy_type in ("individual_policies", "inherited_policies"):
        for option_name, policy_details in data.get(policy_type, {}).items():
            if isinstance(policy_details, dict) and "CC" in policy_details:
                cc_list.append((policy_type, option_name, policy_details["CC"]))

    return cc_list


def get_department_cases(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    department_list = []

    for policy_type in ("individual_policies", "inherited_policies"):
        for option_name, policy_details in data.get(policy_type, {}).items():
            department_info = policy_details.get("Department") or policy_details.get("Departments") \
                if isinstance(policy_details, dict) else None
            if department_info:
                department_list.append((policy_type, option_name, department_info))

    return department_list


ct_cases = get_ct_cases('data/userCred.json')
cc_cases = get_cc_cases('data/userCred.json')
department_cases = get_department_cases('data/userCred.json')


def _verify_inbox_before_call(user_context, operator_username, option_name):
    userCredentials = _load_user_credentials()

    external_user = userCredentials.get("external_user") or userCredentials.get("ExternalUser")
    assert external_user, "No external user credentials found in JSON"

    operator_user_page = None
    external_user_page = None

    try:
        operator_user_page = user_context.new_page(permissions=['camera', 'microphone'])
        external_user_page = user_context.new_page(permissions=['camera', 'microphone'])

        operator_page = LoginPage(operator_user_page)
        external_page = LoginPage(external_user_page)
        operator_call_page = DpAppPage(operator_user_page)

        operator_page.login(operator_username, userCredentials["common password"])
        external_page.login(external_user["username"], external_user["password"])
        time.sleep(5)

        if operator_call_page.is_active_call():
            print("Active call detected after login, hanging up...")
            operator_call_page.hang_up()
            time.sleep(3)

        remove_content_only = is_remove_content_only(option_name)
        operator_call_page.verify_inbox_before_call(external_user['displayName'], remove_content_only)

    finally:
        if operator_user_page:
            operator_user_page.close()
        if external_user_page:
            external_user_page.close()


class TestCTInboxBeforeCall:

    @pytest.mark.parametrize("policy_type, option_name, CT_info", ct_cases)
    def test_ct_inbox_before_call(self, user_context, policy_type, option_name, CT_info):
        print(f"\n--- Running inbox check for Policy Type: '{policy_type}', Option: '{option_name}' ---")

        assert CT_info
        ct_agent = CT_info.get("Trainee")
        assert ct_agent, f"CT operator not found in {CT_info} for {policy_type} - {option_name}"

        _verify_inbox_before_call(user_context, ct_agent, option_name)


class TestCCInboxBeforeCall:

    @pytest.mark.parametrize("policy_type, option_name, CC_info", cc_cases)
    def test_cc_inbox_before_call(self, user_context, policy_type, option_name, CC_info):
        print(f"\n--- Running inbox check for Policy Type: '{policy_type}', Option: '{option_name}' ---")

        assert CC_info, "No cc info found for this test case"
        cc_agent = CC_info.get("CC Agent")
        assert cc_agent, f"CC operator not found in {CC_info} for {policy_type} - {option_name}"

        _verify_inbox_before_call(user_context, cc_agent, option_name)


class TestDepartmentInboxBeforeCall:

    @pytest.mark.parametrize("policy_type, option_name, department_info", department_cases)
    def test_department_inbox_before_call(self, user_context, policy_type, option_name, department_info):
        print(f"\n--- Running inbox check for Policy Type: '{policy_type}', Option: '{option_name}' ---")

        assert department_info, "No department info found for this test case"
        dep_operator = department_info.get("Dep operator")
        assert dep_operator, f"Department operator not found in {department_info} for {policy_type} - {option_name}"

        _verify_inbox_before_call(user_context, dep_operator, option_name)
