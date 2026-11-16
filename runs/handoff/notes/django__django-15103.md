# Handoff: Make `json_script`'s `element_id` optional

## Issue
`json_script` requires `element_id`, but the reporter used it inside `<template>` where no id is needed. No security or correctness reason to require it; making it optional breaks no tests.

## Files and line ranges
- `django/utils/html.py:64-75` — `json_script(value, element_id)` is the core implementation. It unconditionally emits `'<script id="{}" type="application/json">{}</script>'` via `format_html` (lines 72-75). This is the line to change: default `element_id=None` and omit the `id="..."` attribute when it is `None` (e.g. build the tag with a conditional attribute rather than a fixed format string).
- `django/template/defaultfilters.py:85-91` — the `@register.filter` wrapper `json_script(value, element_id)` just delegates to `_json_script`. Needs the same optional signature so `{{ value|json_script }}` works without an argument.
- `grep -rn "def json_script"` confirmed these are the only two definitions; no other call sites or validation of `element_id` exist.

## Tests
- `tests/utils_tests/test_html.py:154-174` — `test_json_script` covers escaping cases but always passes `'test_id'`. Add a case asserting `json_script(value)` omits the `id` attribute.
- `tests/template_tests/filter_tests/test_json_script.py:6-19` — `test_basic` uses `{{ value|json_script:"test_id" }}`. Add a filter test without an argument.

## Docs
- `docs/ref/templates/builtins.txt:1827-1839` — `json_script` filter docs; note the argument is optional.
- `docs/releases/2.1.txt` — prior release notes mentioning `json_script`; add a new release note for this change.

## Ruled out
No security rationale for a mandatory id; no validation logic; no other code references `element_id` for this filter. Existing tests only exercise string ids, so they remain valid.

## Conclusion
The change is safe and localized: make `element_id` optional in both `django/utils/html.py` and `django/template/defaultfilters.py`, conditionally omit the `id` attribute, and extend the two test files plus docs.
