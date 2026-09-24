import json
import time
import pytest

from pages.dpAppPage import DpAppPage
from pages.loginPage import LoginPage
from utils.apihelper import ApiHelpers
from utils.configReader import Configreader
from utils.call_recorder import record_call


def get_department_cases(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    cc_list = []

    # Process individual_policies
    individual_policies = data.get("individual_policies", {})
    for option_name, policy_details in individual_policies.items():
        if isinstance(policy_details, dict) and "CC" in policy_details:
            cc_list.append(("individual_policies", option_name, policy_details["CC"]))

    # Process inherited_policies
    inherited_policies = data.get("inherited_policies", {})
    for option_name, policy_details in inherited_policies.items():
        if isinstance(policy_details, dict) and "CC" in policy_details:
            cc_list.append(("inherited_policies", option_name, policy_details["CC"]))

    return cc_list


cc_cases = get_department_cases('data/userCred.json')


class TestCCPolicies:

    @pytest.mark.parametrize("policy_type, option_name, CC_info", cc_cases)
    def test_cc_calls(self, user_context, policy_type, option_name, CC_info):
        with open('data/userCred.json') as f:
            userCredentials = json.load(f)

        # --- Print the policy type and option name here ---
        print(f"\n--- Running test for Policy Type: '{policy_type}', Option: '{option_name}' ---")
        # --------------------------------------------------

        assert CC_info, "No cc info found for this test case"

        cc_name = CC_info.get("CC Name")
        cc_number = CC_info.get("CC Number")
        cc_agent = CC_info.get("CC Agent")

        assert cc_name, f"CC Name not found in {CC_info} for {policy_type} - {option_name}"
        assert cc_number, f"CC Number not found in {CC_info} for {policy_type} - {option_name}"
        assert cc_agent, f"CC operator not found in {CC_info} for {policy_type} - {option_name}"

        # Fallback to external user credentials for login
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

            operator_page.login(cc_agent, userCredentials["common password"])
            external_page.login(external_user["username"], external_user["password"])
            time.sleep(5)
            print("------->>>>>")

            if operator_call_page.is_active_call():
                print("Active call detected after login, hanging up...")
                operator_call_page.hang_up()
                time.sleep(3)
            else:
                print("no active call")

            operator_api_helper.setOndutystatus(url=conf_reader.get('DEFAULT', 'DUTY_STATUS'),
                                                bearer_token=bearer_token, user_id=conf_reader.get(
                    'USER ID',
                    f'{cc_agent}'))

            time.sleep(5)

            # ---------- Inbound Call ---------
            external_call_page.make_call(str(cc_number))
            operator_call_page.receive_call()
            external_call_page.mute()
            operator_call_page.play_audio('data/testvoice2.mp3')
            external_call_page.sendMessage()
            print(cc_number)

            # Check if bearer_token was successfully retrieved before using it
            if bearer_token:
                callid = operator_api_helper.get_callId(url=conf_reader.get('DEFAULT', 'ACTIVE_CALLS_API'),
                                                        headers=operator_api_helper.get_headers(method_type="get",
                                                                                                bearer_token=bearer_token,
                                                                                                user_id=conf_reader.get(
                                                                                                    'USER ID',
                                                                                                    f'{cc_agent}')),
                                                        key_path="0.entry_point_call_id")
                print(
                    f"Inbound Call id for '{cc_name}' ({policy_type} - {option_name}): Inbound: https://dialpadbeta.com/csr/call/{callid}")
                record_call(cc_name, "Inbound", callid)
            else:
                print(
                    f"Skipped fetching Call ID for '{cc_name}' ({policy_type} - {option_name}) as bearer token was not available.")

            operator_call_page.hang_up()
            time.sleep(5)

            # ----------- Outbound Call ---------

            operator_call_page.makeOutboundAs(external_user['phoneNumber'], cc_name)
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
                                                                                                    f'{cc_agent}')),
                                                        key_path="0.entry_point_call_id")
                print(
                    f"Outbound Call id for '{cc_name}' ({policy_type} - {option_name}): Outbound:  https://dialpadbeta.com/csr/call/{callid}")
                record_call(cc_name, "Outbound", callid)
            else:
                print(
                    f"Skipped fetching Call ID for '{cc_name}' ({policy_type} - {option_name}) as bearer token was not available.")

            operator_call_page.hang_up()
            time.sleep(5)

            # ---------- Missed and voicemail --------------

            external_call_page.make_call(str(cc_number))
            external_call_page.sendMessage()
            time.sleep(6)

            if bearer_token:
                callid = operator_api_helper.get_callId(url=conf_reader.get('DEFAULT', 'ACTIVE_CALLS_API'),
                                                        headers=operator_api_helper.get_headers(method_type="get",
                                                                                                bearer_token=bearer_token,
                                                                                                user_id=conf_reader.get(
                                                                                                    'USER ID',
                                                                                                    f'{cc_agent}')),
                                                        key_path="0.entry_point_call_id")
                print(
                    f"Missed and voicemail Call id for '{cc_name}' ({policy_type} - {option_name}): VM: https://dialpadbeta.com/csr/call/{callid}")
                record_call(cc_name, "VM", callid)
            else:
                print(
                    f"Skipped fetching Call ID for '{cc_name}' ({policy_type} - {option_name}) as bearer token was not available.")

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
