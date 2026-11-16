## Handoff note

**Issue:** `django.utils.html.json_script()` hardcodes `DjangoJSONEncoder`, preventing callers from customizing JSON encoding. The utility is also undocumented, while the template filter counterpart is documented.

**Relevant code:**
- `django/utils/html.py`: `json_script()` at lines 62–78. The hardcoded encoder is at line 70: `json.dumps(value, cls=DjangoJSONEncoder)`. The `DjangoJSONEncoder` import is local at line 69.
- `docs/ref/utils.txt`: `django.utils.html` section starts at line 585. `json_script()` is absent and should be documented near the other HTML helpers.
- `docs/releases/4.2.txt`: add a release note for the new parameter.
- `docs/ref/templates/builtins.txt`: lines 1833+ document the `json_script` template filter; no filter API change is needed.

**Tests:**
- `tests/utils_tests/test_html.py`: `test_json_script()` at lines 180–213 and `test_json_script_without_id()` at lines 214–216. Add coverage for a custom encoder and confirm the default remains `DjangoJSONEncoder`.
- `tests/template_tests/filter_tests/test_json_script.py`: existing filter tests; no changes expected unless filter behavior changes.

**Ruled out:** Changing the template filter signature/behavior; replacing `DjangoJSONEncoder` as the default; moving the encoder import globally without need.

**Conclusion:** Add an `encoder=DjangoJSONEncoder` parameter to `json_script()` and pass it to `json.dumps()`. Document the utility in `docs/ref/utils.txt`, add a 4.2 release note, and test both default and custom encoder paths.
