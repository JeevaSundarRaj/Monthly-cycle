import time
from dataclasses import dataclass

from pages.dpAppPage import DpAppPage
from pages.loginPage import LoginPage
from utils.apihelper import ApiHelpers
from utils.call_recorder import record_call
from utils.configReader import Configreader
from utils.creds import get_external_user, load_creds


@dataclass
class CallEntity:
    """What differs between CC, Department and Coaching Team call scenarios."""
    kind: str                       # label only: "CC" | "Department" | "CT"
    name: str
    number: str                     # number the external user dials
    operator: str                   # operator login (also the 'USER ID' config key)
    set_duty_status: bool = False   # CC agents must be put on duty first
    outbound_as_entity: bool = True  # outbound placed "as" the entity; CT uses a plain call
    vm_pre_decline_wait: int = 6    # wait after the external user leaves a ring-through
    vm_post_decline_wait: int = 13  # wait after the operator declines, before the voicemail audio
    outbound_post_wait: int = 0


def _record_call_id(helper, conf, bearer_token, entity, label, call_type, desc):
    if not bearer_token:
        print(f"Skipped fetching Call ID for '{entity.name}' ({desc}) as bearer token was not available.")
        return
    callid = helper.get_callId(
        url=conf.get('DEFAULT', 'ACTIVE_CALLS_API'),
        headers=helper.get_headers(method_type="get", bearer_token=bearer_token,
                                   user_id=conf.get('USER ID', f'{entity.operator}')),
        key_path="0.entry_point_call_id")
    print(f"{label} Call id for '{entity.name}' ({desc}): https://dialpadbeta.com/csr/call/{callid}")
    record_call(entity.name, call_type, callid)


def run_call_scenario(user_context, entity: CallEntity, desc: str):
    """Inbound, outbound and missed/voicemail calls against one entity, recording every call id."""
    creds = load_creds()
    external_user = get_external_user(creds)
    conf = Configreader()
    client_id = conf.get('CLIENT SECRETS', 'CLIENT_ID')
    client_secret = conf.get('CLIENT SECRETS', 'CLIENT_SECRET')

    operator_user_page = external_user_page = operator_call_page = None
    try:
        operator_user_page = user_context.new_page(permissions=['camera', 'microphone'])
        external_user_page = user_context.new_page(permissions=['camera', 'microphone'])

        operator_call_page = DpAppPage(operator_user_page)
        external_call_page = DpAppPage(external_user_page)
        helper = ApiHelpers(operator_user_page)
        bearer_token = helper.get_bearer_token(client_id=client_id, client_secret=client_secret)

        LoginPage(operator_user_page).login(entity.operator, creds["common password"])
        LoginPage(external_user_page).login(external_user["username"], external_user["password"])
        time.sleep(5)

        if operator_call_page.is_active_call():
            print("Active call detected after login, hanging up...")
            operator_call_page.hang_up()
            time.sleep(3)
        else:
            print("no active call")

        if entity.set_duty_status:
            helper.setOndutystatus(url=conf.get('DEFAULT', 'DUTY_STATUS'), bearer_token=bearer_token,
                                   user_id=conf.get('USER ID', f'{entity.operator}'))
            time.sleep(5)

        # ---------- Inbound ----------
        external_call_page.make_call(str(entity.number))
        operator_call_page.receive_call()
        external_call_page.mute()
        operator_call_page.play_audio('data/testvoice2.mp3')
        external_call_page.sendMessage()
        _record_call_id(helper, conf, bearer_token, entity, "Inbound", "Inbound", desc)
        operator_call_page.hang_up()
        time.sleep(5)

        # ---------- Outbound ----------
        if entity.outbound_as_entity:
            operator_call_page.makeOutboundAs(external_user['phoneNumber'], entity.name)
        else:
            operator_call_page.make_call(external_user['phoneNumber'])
        external_call_page.receive_call()
        operator_call_page.mute()
        external_call_page.play_audio('data/testvoice2.mp3')
        external_call_page.sendMessage()
        if entity.outbound_post_wait:
            time.sleep(entity.outbound_post_wait)
        _record_call_id(helper, conf, bearer_token, entity, "Outbound", "Outbound", desc)
        operator_call_page.hang_up()
        time.sleep(5)

        # ---------- Missed and voicemail ----------
        external_call_page.make_call(str(entity.number))
        external_call_page.sendMessage()
        time.sleep(entity.vm_pre_decline_wait)
        _record_call_id(helper, conf, bearer_token, entity, "Missed and voicemail", "VM", desc)
        operator_call_page.decline_call()
        time.sleep(entity.vm_post_decline_wait)
        external_call_page.play_audio('data/testvoice.mp3')
        external_call_page.hang_up()
    finally:
        try:
            if operator_call_page:
                operator_call_page.hang_up()
        except Exception:
            pass
        for p in (operator_user_page, external_user_page):
            if p:
                p.close()
