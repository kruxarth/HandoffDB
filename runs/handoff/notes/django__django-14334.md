## Handoff note

**Issue:** `LocaleMiddleware` maps `Accept-Language: zh-Hant-HK` to `zh-hans` when `settings.LANGUAGES` lists `zh-hans` before `zh-hant`; expected `zh-hant`.

**Key code:** `django/utils/translation/trans_real.py`
- `get_supported_language_variant()` lines 464–493. Bug is the non-strict fallback loop at lines 490–493: it iterates `supported_lang_codes` and returns the first code starting with the generic prefix (`zh-`), so `zh-hans` wins by settings order. It never tries the parent variant `zh-hant` for input `zh-hant-hk`.
- `get_language_from_request()` lines 515–550, especially Accept-Language handling at 539–550; it delegates to the faulty function.

**Related data:** `django/conf/locale/__init__.py` lines 581–610 defines Chinese fallbacks (`zh-hk` → `zh-hant`, etc.), but there is no `zh-hant-hk` entry, so `LANG_INFO` lookup at `trans_real.py:480` does not help.

**Tests:** `tests/i18n/tests.py`
- Lines 1360–1415 cover Accept-Language/Chinese behavior, including `zh-hant`; missing `zh-hant-hk`.
- Lines 1470–1488 unit-test `get_supported_language_variant`; add regression coverage here and/or around line 1395.

**Docs:** `docs/topics/i18n/translation.txt` (LocaleMiddleware/language selection) and `docs/ref/settings.txt` (`LANGUAGES`) are the relevant references.

**Ruled out:** `LocaleMiddleware` itself; `django/utils/translation/trans_null.py:63–67` (only handles `LANGUAGE_CODE`); Accept-Language parsing; missing `zh-hk` fallback data.

**Conclusion:** Root cause is the `trans_real.py:490–493` fallback loop returning the first supported generic-prefix match instead of preferring a more specific parent variant such as `zh-hant`.
