# Handoff: case-insensitive Accept-Language handling

**Issue:** Django matched language tags case-sensitively, so Firefox’s `zh-tw,zh;q=0.8,...` failed to resolve to Traditional Chinese while Chrome’s `zh-TW,...` worked. RFC 2616/BCP 47 require case-insensitive matching. The issue also asked to correct docs claiming tags are always lowercase.

**Key code (`django/utils/translation/trans_real.py`):**
- `parse_accept_lang_header()` L588–596: already calls `lang_string.lower()` at L596, so header parsing itself is fine.
- `get_supported_language_variant()` L485–520: looks up `lang_code` in `LANG_INFO`/`get_languages()` without normalizing case — the likely remaining bug.
- `get_language_from_request()` L540–585: L569 passes `accept_lang` through unnormalized; the cookie check around L560–566 (`lang_code in get_languages()`) is also case-sensitive.
- `language_code_re` L47–49 already uses `re.IGNORECASE`.
- `django/utils/translation/__init__.py` L221–243: `to_language`/`to_locale` lowercase internally; wrapper at L254.
- `django/conf/locale/__init__.py` L587–615: `zh-tw` → `zh-hant` fallback entries.

**Tests (`tests/i18n/tests.py`):** `test_parse_spec_http_header` ~L1712, `test_parse_literal_http_header` ~L1760, `test_get_supported_language_variant_real` L1910, `test_get_language_from_path_real` L1960 (BCP 47 `en-Latn-US` at L1949), `CountrySpecificLanguageTests.test_get_language_from_request` L2239 (mixed-case `en-US`).

**Docs:** `docs/topics/i18n/index.txt` L74–79 already states the header is case-insensitive, so that half appears fixed. `docs/releases/1.7.txt` L1410–1412 records `parse_accept_lang_header()` lowercasing.

**Ruled out:** header parsing, regex validation, `to_locale`/`to_language`, and the docs sentence.

**Conclusion:** normalize `lang_code` (`.lower()`) before `LANG_INFO`/language lookups in `get_supported_language_variant()`/`get_language_from_request()`, and add a mixed-case `Accept-Language` regression test. Runtime verification was blocked (missing `asgiref`, no network).
