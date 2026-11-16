# Handoff: Select2 subtag translations

**Issue:** With `LANGUAGE_CODE="pt-BR"` (and similar mixed-case/subtag codes), admin autocomplete/select2 does not load `admin/js/vendor/select2/i18n/pt-BR.js`; no i18n file is added to media.

**Key code:**
- `django/contrib/admin/widgets.py:363-373` — `SELECT2_TRANSLATIONS` is built with lowercased keys (`{x.lower(): x ...}`), so `'pt-BR'` becomes key `'pt-br'`; `zh-hans`/`zh-hant` are special-cased at line 373.
- `django/contrib/admin/widgets.py:452-464` — `AutocompleteMixin.media` does `SELECT2_TRANSLATIONS.get(get_language())` and appends `i18n/%s.js`; lookup uses raw `get_language()`.
- `django/contrib/admin/widgets.py:17` — imports `get_language`.

**Cause/conclusion:** `get_language()` can return mixed-case codes such as `pt-BR`, but mapping keys are lowercase, so line 452 misses and `i18n_file` is empty. Normalize the lookup, e.g. `SELECT2_TRANSLATIONS.get(get_language().lower())`, or make lookup case-insensitive. The asset exists: `django/contrib/admin/static/admin/js/vendor/select2/i18n/pt-BR.js`.

**Tests:** `tests/admin_widgets/test_autocomplete_widget.py::test_media` (lines 138-167) covers `de`, nonexistent `00`, `sr-cyrl`, `zh-hans`, `zh-hant`, but not `pt-BR`/`pt-br`. Add a regression case expecting `admin/js/vendor/select2/i18n/pt-BR.js`. No existing docs mention this; consider a `docs/releases/4.1.txt` note if fixing.

**Ruled out:** Missing select2 i18n asset (present) and media path construction (correct); issue is only case-sensitive lookup.
