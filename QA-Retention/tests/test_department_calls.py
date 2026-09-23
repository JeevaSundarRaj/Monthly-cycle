import json
import time
import pytest
from pages.dpAppPage import DpAppPage
from pages.loginPage import LoginPage
from utils.apihelper import ApiHelpers
from utils.configReader import Configreader
from utils.call_recorder import record_call
from utils.retention_policy import is_remove_content_only


def get_department_cases(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    departments_list = []

    # Process individual_policies
    individual_policies = data.get("individual_policies", {})
    for option_name, policy_details in individual_policies.items():
        if isinstance(policy_details, dict) and "Departments" in policy_details:
            departments_list.append(("individual_policies", option_name, policy_details["Departments"]))

    # Process inherited_policies
    inherited_policies = data.get("inherited_policies", {})
    for option_name, policy_details in inherited_policies.items():
        if isinstance(policy_details, dict) and "Departments" in policy_details:
            departments_list.append(("inherited_policies", option_name, policy_details["Departments"]))

    return departments_list


department_cases = get_department_cases('data/userCred.json')


class TestDepartmentPolicies:

    @pytest.mark.parametrize("policy_type, option_name, department_info", department_cases)
    def test_department_calls(self, user_context, subtests, policy_type, option_name, department_info):
        with open('data/userCred.json') as f:
            userCredentials = json.load(f)

        print(f"\n--- Running test for Policy Type: '{policy_type}', Option: '{option_name}' ---")
        # --------------------------------------------------

        assert department_info, "No department info found for this test case"

        department_name = department_info.get("Department Name")
        department_number = department_info.get("Department Number")
        dep_operator = department_info.get("Dep operator")

        assert department_name, f"Department Name not found in {department_info} for {policy_type} - {option_name}"
        assert department_number, f"Department Number not found in {department_info} for {policy_type} - {option_name}"
        assert dep_operator, f"Department operator not found in {department_info} for {policy_type} - {option_name}"

        external_user = userCredentials.get("external_user") or userCredentials.get("ExternalUser")
        assert external_user, "No external user credentials found in JSON"

        conf_reader = Configreader()
        external_user_page = None
        operator_user_page = None
        operator_call_page = None

        client_id = conf_reader.get('CLIENT SECRETS', 'CLIENT_ID')
        client_secret = conf_reader.get('CLIENT SECRETS', 'CLIENT_SECRET')

        try:
            operator_user_page = user_context.new_page(permissions=['camera', 'microphone'])
            external_user_page = user_context.new_page(permissions=['camera', 'microphone'])

            operator_page = LoginPage(operator_user_page)
            external_page = LoginPage(external_user_page)
            operator_call_page = DpAppPage(operator_user_page)
            external_call_page = DpAppPage(external_user_page)

            operator_api_helper = ApiHelpers(operator_user_page)

            operator_page.login(dep_operator, userCredentials["common password"])
            external_page.login(external_user["username"], external_user["password"])
            time.sleep(5)

            print("------->>>>>")

            if operator_call_page.is_active_call():
                print("Active call detected after login, hanging up...")
                operator_call_page.hang_up()
                time.sleep(3)
            else:
                print("no active call")

            remove_content_only = is_remove_content_only(option_name)
            with subtests.test(msg="inbox_check_before_call"):
                operator_call_page.verify_inbox_before_call(external_user['displayName'], remove_content_only)

            # ---------- Inbound Call ---------
            external_call_page.make_call(str(department_number))
            operator_call_page.receive_call()
            external_call_page.mute()
            operator_call_page.play_audio('data/testvoice2.mp3')
            external_call_page.sendMessage()
            print(department_number)

            bearer_token = operator_api_helper.get_bearer_token(client_id=client_id, client_secret=client_secret)

            # Check if bearer_token was successfully retrieved before using it
            if bearer_token:
                callid = operator_api_helper.get_callId(url=conf_reader.get('DEFAULT', 'ACTIVE_CALLS_API'),
                                                        headers=operator_api_helper.get_headers(method_type="get",
                                                                                                bearer_token=bearer_token,
                                                                                                user_id=
                                                                                                conf_reader.get(
                                                                                                    'USER ID',
                                                                                                    f'{dep_operator}')),
                                                        key_path="0.entry_point_call_id")
                print(
                    f"Inbound Call id for '{department_name}' ({policy_type} - {option_name}): Inbound:  https://dialpadbeta.com/csr/call/{callid}")
                record_call(department_name, "Inbound", callid)
            else:
                print(
                    f"Skipped fetching Call ID for '{department_name}' ({policy_type} - {option_name}) as bearer token was not available.")

            operator_call_page.hang_up()
            time.sleep(5)

            # ----------- Outbound Call ---------

            operator_call_page.makeOutboundAs(external_user['phoneNumber'], department_name)
            external_call_page.receive_call()
            operator_call_page.mute()
            external_call_page.play_audio('data/testvoice2.mp3')
            external_call_page.sendMessage()

            if bearer_token:
                callid = operator_api_helper.get_callId(url=conf_reader.get('DEFAULT', 'ACTIVE_CALLS_API'),
                                                        headers=operator_api_helper.get_headers(method_type="get",
                                                                                                bearer_token=bearer_token,
                                                                                                user_id=conf_reader.get(
                                                                                                    'USER ID',
                                                                                                    f'{dep_operator}')),
                                                        key_path="0.entry_point_call_id")
                print(
                    f"Outbound Call id for '{department_name}' ({policy_type} - {option_name}): Outbound:  https://dialpadbeta.com/csr/call/{callid}")
                record_call(department_name, "Outbound", callid)
            else:
                print(
                    f"Skipped fetching Call ID for '{department_name}' ({policy_type} - {option_name}) as bearer token was not available.")

            operator_call_page.hang_up()
            time.sleep(5)

            # ---------- Missed and voicemail --------------
            external_call_page.make_call(str(department_number))
            external_call_page.sendMessage()
            time.sleep(10)

            if bearer_token:
                callid = operator_api_helper.get_callId(url=conf_reader.get('DEFAULT', 'ACTIVE_CALLS_API'),
                                                        headers=operator_api_helper.get_headers(method_type="get",
                                                                                                bearer_token=bearer_token,
                                                                                                user_id=
                                                                                                conf_reader.get(
                                                                                                    'USER ID',
                                                                                                    f'{dep_operator}')),
                                                        key_path="0.entry_point_call_id")
                print(
                    f"Missed and voicemail Call id for '{department_name}' ({policy_type} - {option_name}): VM: https://dialpadbeta.com/csr/call/{callid}")
                record_call(department_name, "VM", callid)
            else:
                print(
                    f"Skipped fetching Call ID for '{department_name}' ({policy_type} - {option_name}) as bearer token was not available.")

            operator_call_page.decline_call()
            time.sleep(10)
            external_call_page.play_audio("data/testvoice.mp3")

            external_call_page.hang_up()


        finally:
            try:
                if operator_call_page:
                    operator_call_page.hang_up()
            except Exception:
                pass
            if operator_user_page:
                operator_user_page.close()
            if external_user_page:
                external_user_page.close()
