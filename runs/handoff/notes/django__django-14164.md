# Handoff: `to_locale()` is not idempotent

## Issue
`to_locale()` returns `'en_US'` for `'en-us'` but `'en_us'` for `'en_US'`, so it is not idempotent. This surfaces when locale codes (e.g. `pt_BR`, `zh_Hans`) are passed to `translation.override()`/`activate()`, which expect language codes.

## Code that matters
- `django/utils/translation/__init__.py:202-217` — `to_locale()`. Root cause: it calls `language.lower()` and then `partition('-')`, so an existing `_` separator is never recognised and the country subtag gets lowercased. `to_language()` at `:193-200` has the mirror-image logic and is *not* the bug.
- `django/utils/translation/trans_real.py:137` — `DjangoTranslation.__init__` stores `self.__locale = to_locale(language)`; a non-idempotent result here means a locale string is treated as a distinct language.
- `django/utils/translation/trans_real.py:262-267` (`translation()`) — `_translations` cache is keyed by the raw language string, so `'pt_BR'` and `'pt-br'` create separate entries.
- `django/utils/translation/trans_real.py:450` — `check_for_language()` also feeds language codes into `to_locale()`.
- `override()`/`activate()` in `django/utils/translation/__init__.py` just forward to `trans_real.activate`, so no change is needed there.

## Tests and docs
- `tests/i18n/tests.py:310-328` — `test_to_locale`; add cases asserting `to_locale(to_locale(x)) == to_locale(x)` for `en_US`, `pt_BR`, `zh_Hans`, `sr_Latn`, `nl_NL-x-informal`.
- `tests/i18n/tests.py:330-332` — `test_to_language`, for symmetry.
- `docs/topics/i18n/translation.txt` and `docs/ref/utils.txt` — language-code vs locale-code documentation; update only if behaviour is not made idempotent.

## Ruled out
`to_language()`, catalog lookup/fallback in `DjangoTranslation`, and the `_translations` cache were investigated; none need modification — fixing `to_locale()` alone makes both spellings converge.

## Conclusion
Normalise `_` to `-` before parsing in `to_locale()` (e.g. `language = language.replace('_', '-')`) so `'en_US'` → `'en-us'` → `'en_US'`. Keeps existing output for all current test cases and makes the function idempotent.
