# Handoff: i18n_patterns 404 for locales with script + region

## Issue
`i18n_patterns()` returns 404 for language codes containing both a script and a region subtag (e.g. `en-latn-us`, `en-Latn-US`), while `en-us` works. Expected: 200. Code must accept RFC 5646 langtags (`language-script-region-variant...`).

## Root cause / key files
- **`django/utils/translation/trans_real.py:46`** — `language_code_prefix_re = r'^/(\w+([@-]\w+)?)(/|$)'`. This only allows **one** optional `@`/`-` segment, so `/en-latn-us/` fails to match. This is the primary bug.
- **`django/utils/translation/trans_real.py:501-511`** — `get_language_from_path()` uses that regex; fixing the regex here fixes URL prefix extraction.
- **`django/urls/resolvers.py:305-336`** — `LocalePrefixPattern` (`language_prefix` at 316-322) builds the prefix regex from `get_language()`; verify it accepts the longer code once parsing succeeds.
- **`django/utils/translation/__init__.py:193-215`** — `to_language()`/`to_locale()` already normalize `sr-latn` → `sr_Latn`, so they are not the fault.

## Tests
- `tests/i18n/tests.py`: `test_to_locale` (~313-337), `test_get_language_from_path_real` (1601-1611), `test_page_with_dash` (1816), `UnprefixedDefaultLanguageTests` (~1797+).
- `tests/i18n/patterns/tests.py` + `tests/i18n/patterns/urls/default.py` — add `en-latn-us`/`en-Latn-US` to `LANGUAGES` and assert 200.
- `tests/check_framework/test_translation.py` — validates language tags via `language_code_re`.

## Docs
`docs/topics/i18n/translation.txt` (~1304, `i18n_patterns`) and the language-code term reference.

## Ruled out
`language_code_re` (41-44) already permits multiple subtags; `LocaleMiddleware`, `translate_url`, `get_supported_language_variant` fallback logic, and `to_locale` script capitalization are all fine.

## Conclusion
The prefix regex at `trans_real.py:46` is too restrictive. Widen it to allow multiple `-`-separated subtags (keeping `@` support), then add regression tests for `en-latn-us` and `en-Latn-US`.
