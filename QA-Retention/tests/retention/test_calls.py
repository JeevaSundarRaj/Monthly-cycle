import pytest

from utils.call_flow import CallEntity, run_call_scenario
from utils.creds import get_policy_cases

pytestmark = pytest.mark.calls

cc_cases = get_policy_cases("CC")
ct_cases = get_policy_cases("CT")
# inherited Option 2 is keyed "Departments", the rest "Department"
department_cases = get_policy_cases("Department", "Departments")


def _require(info, desc, **fields):
    assert info, f"No info found for {desc}"
    for key, label in fields.items():
        assert info.get(key), f"{label} not found in {info} for {desc}"
    return {key: info[key] for key in fields}


class TestCCPolicies:

    @pytest.mark.parametrize("policy_type, option_name, info", cc_cases)
    def test_cc_calls(self, user_context, policy_type, option_name, info):
        desc = f"{policy_type} - {option_name}"
        print(f"\n--- Running CC call test for {desc} ---")
        f = _require(info, desc, **{"CC Name": "CC Name", "CC Number": "CC Number", "CC Agent": "CC operator"})
        run_call_scenario(user_context, CallEntity(
            kind="CC", name=f["CC Name"], number=f["CC Number"], operator=f["CC Agent"],
            set_duty_status=True,
        ), desc)


class TestDepartmentPolicies:

    @pytest.mark.parametrize("policy_type, option_name, info", department_cases)
    def test_department_calls(self, user_context, policy_type, option_name, info):
        desc = f"{policy_type} - {option_name}"
        print(f"\n--- Running Department call test for {desc} ---")
        f = _require(info, desc, **{"Department Name": "Department Name",
                                    "Department Number": "Department Number",
                                    "Dep operator": "Department operator"})
        run_call_scenario(user_context, CallEntity(
            kind="Department", name=f["Department Name"], number=f["Department Number"],
            operator=f["Dep operator"], vm_pre_decline_wait=10, vm_post_decline_wait=10,
        ), desc)


class TestCTPolicies:

    @pytest.mark.parametrize("policy_type, option_name, info", ct_cases)
    def test_ct_calls(self, user_context, policy_type, option_name, info):
        desc = f"{policy_type} - {option_name}"
        print(f"\n--- Running CT call test for {desc} ---")
        f = _require(info, desc, **{"Coaching team": "CT name", "CT Trainee Number": "CT number",
                                    "Trainee": "CT trainee"})
        run_call_scenario(user_context, CallEntity(
            kind="CT", name=f["Coaching team"], number=f["CT Trainee Number"], operator=f["Trainee"],
            outbound_as_entity=False, vm_pre_decline_wait=5, outbound_post_wait=5,
        ), desc)
