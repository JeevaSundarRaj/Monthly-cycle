import os
import re
from datetime import datetime

RESULTS_DIR = "results"

# test function name -> plan case(s); anything unlisted is reported with an empty plan case
PLAN_CASES = {
    "test_cc_calls": "Retention: individual/inherited policy Options 1-3 (CC call flow)",
    "test_department_calls": "Retention: individual/inherited policy Options 1-3 (Department call flow)",
    "test_ct_calls": "Retention: individual/inherited policy Options 1-3 (CT call flow)",
    "test_check_inbox": "Retention: Options 1-3 inbox check",
    "test_inherit_office_policy_for_department_and_ct": "Retention: inherit office policy for Department and CT",
    "test_remove_policy_from_retention_policy_page": "Retention: remove policy from Retention Policy page",
    "test_contact_center_retention_policy": "Retention: set new policy for Call centre",
    "test_department_retention_policy": "Retention: set policy for Department (admin)",
    "test_coaching_team_retention_policy": "Retention: set policy for Coaching Team (admin)",
    "test_create_from_scratch": "CM & LCC: create new card from scratch",
    "test_edit_and_delete": "CM & LCC: edit and delete card",
    "test_duplicate_and_delete": "CM & LCC: duplicate and delete card",
    "test_live_coach_card_preview": "LCC: preview live coach card",
    "test_create_from_template": "LCC: create card from template",
    "test_template_card_edit_delete": "LCC: preview/edit/delete card from template",
    "test_geo_routing": "Geo-Routing: create geo-routing, route to correct CC, fallback to Dept",
    "test_add_local_number": "Geo-Routing: add local number",
    "test_business_hours_change": "Geo-Routing: call routing to CC in business hours",
    "test_closed_hours_transcription": "Geo-Routing: call routing to CC in closed hours",
    "test_call_routing_cc_24x7": "Geo-Routing: call routing to CC 24x7",
    "test_ai_on_off_transcription": "Geo-Routing: inbound call with Voice AI (enable/disable)",
}

_rows = {}


def _result_of(report, reason):
    if report.failed:
        return "FAIL" if report.when == "call" else "ERROR"
    if report.skipped:
        return "NOT AUTOMATED" if reason.startswith("TODO") else "SKIPPED"
    return "PASS"


def record_report(report):
    """Keep one row per test: the call phase, unless setup/teardown failed or the test was skipped."""
    if report.when == "call" or (report.when in ("setup", "teardown") and (report.failed or report.skipped)):
        if report.when == "teardown" and report.nodeid in _rows and _rows[report.nodeid][3] != "PASS":
            return
        reason = ""
        if report.failed:
            reason = report.longreprtext.strip().splitlines()[-1] if report.longreprtext else ""
        elif report.skipped and isinstance(report.longrepr, tuple):
            reason = str(report.longrepr[2]).replace("Skipped: ", "")
        reason = re.sub(r"\s+", " ", reason)[:300]
        func = report.nodeid.split("::")[-1].split("[")[0]
        _rows[report.nodeid] = (PLAN_CASES.get(func, ""), report.nodeid, func, _result_of(report, reason),
                                f"{report.duration:.1f}", reason)


ORDER = ("PASS", "FAIL", "ERROR", "NOT AUTOMATED", "SKIPPED")


def write_results():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(RESULTS_DIR, f"test_results_{stamp}.txt")
    rows = sorted(_rows.values(), key=lambda r: (r[0], r[1]))

    lines = [f"Test run {datetime.now():%Y-%m-%d %H:%M:%S}",
             "Summary: " + ", ".join(f"{r}={sum(1 for x in rows if x[3] == r)}" for r in ORDER)
             + f", total={len(rows)}", ""]
    for plan, node, _func, result, duration, reason in rows:
        lines.append(f"[{result}] {plan or '(no plan case)'}")
        lines.append(f"    {node} ({duration}s)")
        if reason:
            lines.append(f"    {reason}")
    text = "\n".join(lines) + "\n"

    for target in (path, os.path.join(RESULTS_DIR, "latest.txt")):
        with open(target, "w") as f:
            f.write(text)
    return path, len(rows)


STATUS_WORD = {"PASS": "PASSED", "FAIL": "FAILED", "ERROR": "ERROR", "NOT AUTOMATED": "SKIPPED", "SKIPPED": "SKIPPED"}


def format_console_summary():
    """One 'test_name - STATUS' line per test, then a totals line."""
    rows = list(_rows.values())
    lines = [f"{func} - {STATUS_WORD[result]}" for _plan, _node, func, result, _d, _r in rows]
    count = lambda *r: sum(1 for x in rows if x[3] in r)
    lines.append(f"Tests run: {len(rows)}, Failures: {count('FAIL')}, Errors: {count('ERROR')}, "
                 f"Skipped: {count('SKIPPED', 'NOT AUTOMATED')}")
    return "\n".join(lines)
