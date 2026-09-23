import json
import time

import pytest

from pages.dpAppPage import DpAppPage
from pages.loginPage import LoginPage
from utils.apihelper import ApiHelpers
from utils.configReader import Configreader
from utils.call_recorder import record_call
from utils.retention_policy import is_remove_content_only


def get_ct_cases(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    ct_list = []

    # Process individual_policies
    individual_policies = data.get("individual_policies", {})
    for option_name, policy_details in individual_policies.items():
        if isinstance(policy_details, dict) and "CT" in policy_details:
            ct_list.append(("individual_policies", option_name, policy_details["CT"]))

    # Process inherited_policies
    inherited_policies = data.get("inherited_policies", {})
    for option_name, policy_details in inherited_policies.items():
        if isinstance(policy_details, dict) and "CT" in policy_details:
            ct_list.append(("inherited_policies", option_name, policy_details["CT"]))

    return ct_list


ct_cases = get_ct_cases('data/userCred.json')


class TestCTPolicies:

    @pytest.mark.parametrize("policy_type, option_name, CT_info", ct_cases)
    def test_ct_calls(self, user_context, subtests, policy_type, option_name, CT_info):
        with open('data/userCred.json') as f:
            userCredentials = json.load(f)

        print(f"\n--- Running test for Policy Type: '{policy_type}', Option: '{option_name}' ---")

        assert CT_info

        ct_name = CT_info.get("Coaching team")
        ct_agent = CT_info.get("Trainee")
        ct_number = CT_info.get("CT Trainee Number")

        assert ct_name, f"CC Name not found in {CT_info} for {policy_type} - {option_name}"
        assert ct_number, f"CC Number not found in {CT_info} for {policy_type} - {option_name}"
        assert ct_agent, f"CC operator not found in {CT_info} for {policy_type} - {option_name}"

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

            bearer_token = operator_api_helper.get_bearer_token(client_id=client_id, client_secret=client_secret)

            operator_page.login(ct_agent, userCredentials["common password"])
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

            # ----------- Inbound Call ---------
            external_call_page.make_call(str(ct_number))
            operator_call_page.receive_call()
            external_call_page.mute()
            operator_call_page.play_audio('data/testvoice2.mp3')
            external_call_page.sendMessage()
            print(ct_number)

            # Check if bearer_token was successfully retrieved before using it
            if bearer_token:
                callid = operator_api_helper.get_callId(url=conf_reader.get('DEFAULT', 'ACTIVE_CALLS_API'),
                                                        headers=operator_api_helper.get_headers(method_type="get",
                                                                                                bearer_token=bearer_token,
                                                                                                user_id=conf_reader.get(
                                                                                                    'USER ID',
                                                                                                    f'{ct_agent}')),
                                                        key_path="0.entry_point_call_id")
                print(
                    f"Inbound Call id for '{ct_name}' ({policy_type} - {option_name}): Inbound: https://dialpadbeta.com/csr/call/{callid}")
                record_call(ct_name, "Inbound", callid)
            else:
                print(
                    f"Skipped fetching Call ID for '{ct_name}' ({policy_type} - {option_name}) as bearer token was not available.")

            operator_call_page.hang_up()
            time.sleep(5)

            # ----------- Outbound Call ---------
            operator_call_page.make_call(external_user['phoneNumber'])
            external_call_page.receive_call()
            operator_call_page.mute()
            external_call_page.play_audio('data/testvoice2.mp3')
            external_call_page.sendMessage()
            time.sleep(5)

            if bearer_token:
                callid = operator_api_helper.get_callId(url=conf_reader.get('DEFAULT', 'ACTIVE_CALLS_API'),
                                                        headers=operator_api_helper.get_headers(method_type="get",
                                                                                                bearer_token=bearer_token,
                                                                                                user_id=conf_reader.get(
                                                                                                    'USER ID',
                                                                                                    f'{ct_agent}')),
                                                        key_path="0.entry_point_call_id")
                print(
                    f"Outbound Call id for '{ct_name}' ({policy_type} - {option_name}): Outbound: https://dialpadbeta.com/csr/call/{callid}")
                record_call(ct_name, "Outbound", callid)
            else:
                print(
                    f"Skipped fetching Call ID for '{ct_name}' ({policy_type} - {option_name}) as bearer token was not available.")

            operator_call_page.hang_up()
            time.sleep(5)

            # ---------- Missed and voicemail --------------

            external_call_page.make_call(str(ct_number))
            external_call_page.sendMessage()
            time.sleep(5)

            if bearer_token:
                callid = operator_api_helper.get_callId(url=conf_reader.get('DEFAULT', 'ACTIVE_CALLS_API'),
                                                        headers=operator_api_helper.get_headers(method_type="get",
                                                                                                bearer_token=bearer_token,
                                                                                                user_id=conf_reader.get(
                                                                                                    'USER ID',
                                                                                                    f'{ct_agent}')),
                                                        key_path="0.entry_point_call_id")
                print(
                    f"Missed and voicemail Call id for '{ct_name}' ({policy_type} - {option_name}): VM: https://dialpadbeta.com/csr/call/{callid}")
                record_call(ct_name, "VM", callid)
            else:
                print(
                    f"Skipped fetching Call ID for '{ct_name}' ({policy_type} - {option_name}) as bearer token was not available.")

            operator_call_page.decline_call()
            time.sleep(13)
            external_call_page.play_audio('data/testvoice.mp3')
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
