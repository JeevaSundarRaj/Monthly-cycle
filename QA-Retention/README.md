# QA-Retention

Playwright + pytest UI automation for the Dialpad monthly regression cycle. It covers:

| Area | Folder | What it checks |
|------|--------|----------------|
| Retention | `tests/retention/` | Admin retention policies (Office, Department, Call Center, Coaching Team), live call flows, and inbox verification per operator (Options 1-3: Cleanup and Archive, Remove Content, Remove Content and PII) |
| AI cards | `tests/ai_cards/` | Conversation Moments (CM) and Live Coach Cards (LCC): create, edit, duplicate, delete, templates, preview |
| Geo-routing | `tests/geo_routing/` | Geo-routing setup, local numbers, business and closed hours, 24x7 routing, Voice AI on/off |

## Project layout

```
pages/        Page objects (admin retention, AI settings, contact center, geo-routing, Dialpad app, login)
tests/        Test suites, grouped by area; tests/conftest.py holds shared fixtures and reporting hooks
utils/        call_flow, call_recorder, creds, result_logger
data/         Test credentials (userCred.json) and audio/image fixtures
results/      Per-run text results (generated)
report/       HTML and JUnit reports (generated)
```

## Setup

Requires Python 3.12+ and Google Chrome.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chrome
```

### Credentials

Tests read `data/userCred.json`. Expected top-level keys:

- `common password`
- `admin_user`, `automation_user2` (`username`, `password`)
- `external_user` (`username`, `password`, `phoneNumber`, `displayName`)
- `admin_retention_targets` (`department_name`, `cc_name`, `ct_name`)
- `individual_policies`, `inherited_policies` (per-option entities and operators)

Do not commit real passwords. Keep the file out of version control or use CI secrets.

## Running tests

```bash
pytest tests                              # everything
pytest tests/retention                    # one area
pytest tests/retention/test_inbox.py      # one file
pytest tests -m "not calls"               # skip live call-flow tests
pytest tests -k test_check_inbox          # by name
```

Locally the browser runs headed. With `CI=true` it runs headless with fake media devices.

Inbox checks (`test_inbox.py`) are automatically ordered before any test that makes new calls.

## Output

At the end of each run the console prints one line per test and a totals line:

```
test_check_inbox - PASSED
test_check_inbox - FAILED
test_cc_calls - PASSED
test_geo_routing - SKIPPED
Tests run: 4, Failures: 1, Errors: 0, Skipped: 1
```

Files written per run:

| File | Contents |
|------|----------|
| `results/test_results_<timestamp>.txt`, `results/latest.txt` | Summary and each test mapped to its test-plan case, with status, duration and failure reason |
| `report/report.html` | Self-contained pytest-html report |
| `report/junit.xml` | JUnit XML for CI |
| `call_summary.csv` | Calls made during the run |

Test-plan names come from `PLAN_CASES` in `utils/result_logger.py`. Add an entry there when you add a test.

## Notes

- Retention removal (Options 2 and 3) is not instant. Content/PII removal can take up to a day, so inbox checks reflect calls made in earlier runs.
- Live call tests need real audio devices (`sounddevice`) and won't run on a stock GitHub-hosted runner; use `-m "not calls"` there.
- `pyobjc-*` and `pyperclipimg` in `requirements.txt` are macOS-only; filter them out on Linux.

## GitHub Actions

Example workflow (`.github/workflows/tests.yml`): store the contents of `data/userCred.json` in a repository secret named `USER_CRED_JSON`, write it to `data/userCred.json` before the run, set `CI=true`, run `pytest tests`, and upload `report/`, `results/` and `call_summary.csv` as artifacts.

## Adding a test

1. Put it in the matching `tests/<area>/` folder, named `test_*.py`.
2. Reuse the page objects in `pages/`; add new locators or actions there, not in the test.
3. Register a plan-case name in `PLAN_CASES` (`utils/result_logger.py`).
4. Mark live call-flow tests with `@pytest.mark.calls`.
