## Handoff: Select2 translation fallback for regional language codes

**Issue:** With `LANGUAGE_CODE` like `"de-ch"`, the autocomplete widget's Select2 UI falls back to English because Select2 has no `de-ch` translation. It should fall back to the generic language (`"de"`) when an exact regional match is unavailable. Not a duplicate of #33070.

**Relevant code:**
- `django/contrib/admin/widgets.py:397-399` — comment documenting the lowercase→Select2 language mapping.
- `django/contrib/admin/widgets.py:400-455` — `SELECT2_TRANSLATIONS` dict; keys are lowercase base codes only (e.g. `"de"`), so `get_language()` returning `"de-ch"` misses.
- `django/contrib/admin/widgets.py:543` — `media` property builds `"admin/js/vendor/select2/i18n/%s.js" % self.i18n_name`; this is where the lookup must gain the fallback.
- `django/contrib/admin/widgets.py:457-480` — `build_attrs`/AJAX attrs, context only.

**Tests:** `tests/admin_widgets/test_autocomplete_widget.py` (see `test_media` at ~line 158) is the right place to assert the generated i18n script path for a regional `LANGUAGE_CODE`. Selenium tests in `tests/admin_views/test_autocomplete_view.py` exercise the rendered widget but are not needed for this unit-level behavior.

**Docs:** Update release notes under `docs/releases/`; admin widget docs live in `docs/ref/contrib/admin/` (not yet reviewed).

**Ruled out:** `admin_views` Selenium selectors (lines 409-517) are unrelated to the translation lookup; `SELECT2_TRANSLATIONS` itself contains no regional entries, so the fix belongs in the `i18n_name` resolution logic, not the static vendor files.

**Conclusion:** In the `media` property (~line 543), when the lowercased `get_language()` value is absent from `SELECT2_TRANSLATIONS`, split on `"-"` and retry with the base code before falling back to no i18n script. Add a regression test in `test_autocomplete_widget.py` for `de-ch` → `i18n/de.js`.
