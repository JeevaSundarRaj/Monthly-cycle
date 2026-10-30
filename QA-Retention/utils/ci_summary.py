"""Render test results + call summary CSV as GitHub Actions job summary markdown."""
import csv
import glob
import os
import sys
import xml.etree.ElementTree as ET


def esc(text):
    return str(text).replace("|", "\\|").replace("\n", "<br>")


def junit_section(path):
    if not os.path.exists(path):
        return ["_No junit.xml found._"]
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    total = sum(int(s.get("tests", 0)) for s in suites)
    fails = sum(int(s.get("failures", 0)) for s in suites)
    errors = sum(int(s.get("errors", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)
    passed = total - fails - errors - skipped
    out = [f"**Total {total} | ✅ Passed {passed} | ❌ Failed {fails} | 💥 Errors {errors} | ⏭️ Skipped {skipped}**", "",
           "| Status | Test | Time (s) | Details |", "|---|---|---|---|"]
    for case in root.iter("testcase"):
        status, detail = "✅ PASS", ""
        for tag, label in (("failure", "❌ FAIL"), ("error", "💥 ERROR"), ("skipped", "⏭️ SKIP")):
            node = case.find(tag)
            if node is not None:
                status, detail = label, (node.get("message") or "")[:300]
                break
        name = f"{case.get('classname', '')}::{case.get('name', '')}"
        out.append(f"| {status} | {esc(name)} | {float(case.get('time', 0)):.1f} | {esc(detail)} |")
    return out


def csv_section(path):
    if not os.path.exists(path):
        return ["_No call_summary.csv found._"]
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return ["_call_summary.csv is empty._"]
    out = ["| " + " | ".join(esc(c) for c in rows[0]) + " |", "|" + "---|" * len(rows[0])]
    for r in rows[1:]:
        out.append("| " + " | ".join(esc(c) for c in r) + " |")
    return out


def main():
    lines = ["## Test results", ""] + junit_section("report/junit.xml")
    lines += ["", "## Call summary (call_summary.csv)", ""] + csv_section("call_summary.csv")
    shots = sorted(glob.glob("dbg_*.png"))
    if shots:
        lines += ["", "## Failure screenshots", "", "Attached in the `test-reports` artifact: " + ", ".join(f"`{s}`" for s in shots)]
    lines += ["", "_Full HTML report, results/*.txt, call.logs, xlsx files and screenshots are in the `test-reports` artifact._"]
    text = "\n".join(lines) + "\n"
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
