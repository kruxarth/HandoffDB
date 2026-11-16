# Handoff: add `nonform` CSS class to FormSet non-form errors

**Issue:** FormSet non-form errors render as `<ul class="errorlist">`, unlike form non-field errors which get `nonfield`. Requested: give formset non-form errors a `nonform` class (and document it) so custom `ErrorList` subclasses can distinguish field / non-field / non-form errors.

**Code that matters:**
- `django/forms/formsets.py:290-298` — `non_form_errors()`; returns `self._non_form_errors`.
- `django/forms/formsets.py:335-336` — `full_clean()` initializes `self._non_form_errors = self.error_class()` with no class argument. **This is the primary change point** → `self.error_class(error_class='nonform')`.
- `django/forms/formsets.py:383` — reassigns `self._non_form_errors = self.error_class(e.error_list)` when a `ValidationError` is raised during cleaning; also needs `error_class='nonform'`.
- `django/forms/forms.py:317,359` — existing `nonfield` usage, the pattern to mirror.
- `django/forms/utils.py:80-90` — `ErrorList.__init__` already accepts `error_class` and appends it to `errorlist`; no change needed.

**Tests:** `tests/forms_tests/tests/test_formsets.py` — `test_non_form_errors` (~974), `test_formset_error_class` (1040), `test_non_form_errors_run_full_clean` (1130), and rendering assertions around 1307-1350 (line ~1319 currently expects `<ul class="errorlist nonfield">`; verify/update). Add an assertion that non-form errors carry `nonform`.

**Docs:** `docs/topics/forms/formsets.txt` (~355-368, the `non_form_errors()` / formset `clean()` section) needs the new class documented; `docs/topics/forms/index.txt:610-615` documents `nonfield` and is a good cross-reference.

**Ruled out:** `forms.py` already handles `nonfield` correctly; `forms/utils.py` needs no change. Other `non_form_errors` matches under `tests/admin_views`, `tests/inline_formsets`, `tests/model_formsets*`, `tests/generic_relations` are consumers, not definitions. No `nonform` string exists anywhere yet.

**Conclusion:** two-line change in `formsets.py` plus docs and test updates.
