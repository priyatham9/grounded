# Consistency check

`tools/check_consistency.py` fails when a headline number differs between the README, the site pages and the papers. It is stdlib-only and offline.

`tools/consistency_claims.json` lists each claim: an id, the canonical value, a source (file plus a regex with one capture group, or a CSV row count) and every file that repeats it. Every match must equal the canonical value, and a pattern that stops matching also fails, so rewording a page forces an update here. `forbidden` entries flag stale wording (for example "three non-LLM baselines").

Run `python3 tools/check_consistency.py`; the test is `python3 -m unittest tools.test_check_consistency`. CI runs both in the `claims` workflow.

Scope: only claims whose truth is in this repo. Numbers from sibling repositories are covered by `claims/`.
