## Handoff note

Issue: `makemessages` rejects valid private-use locales such as `nl-nl-x-informal` / `nl_NL-x-informal` with “invalid locale nl_NL-x-informal, did you mean nl_NL_x_informal?” even though `DjangoTranslation`/`to_locale()` correctly maps `nl-nl-x-informal` to `nl_NL-x-informal`.

Key code:
- `django/core/management/commands/makemessages.py:429-436` — the faulty validation. `if "-" in locale:` treats every hyphen as invalid, including the private-use subtag `-x-informal`. This was introduced by commit `f63f3cdf0969c23fd0c05de0f4a2a1df0cd5112e`.
- `django/core/management/commands/makemessages.py:402-411` — locale directory discovery; regex only filters dirs starting with two lowercase letters, not the rejection source.
- `django/core/management/commands/makemessages.py:676-720` — `write_po_file()` accepts locale names with hyphens and creates `<locale>/LC_MESSAGES`, so downstream writing is not the blocker.
- `django/utils/translation/__init__.py:230-243` — `to_locale()` correctly preserves the `-x-informal` tail as `-x-informal`; not faulty.

Tests:
- `tests/i18n/test_extraction.py:171-185` — `test_valid_locale` / `test_invalid_locale` cover the makemessages validation behavior.
- `tests/i18n/tests.py:424-428` — existing locale-conversion tests explicitly cover `nl-nl-x-informal` → `nl_NL-x-informal`.

Docs: relevant references are `docs/ref/django-admin.txt` (`makemessages`) and `docs/topics/i18n/translation.txt` (locale/language formats); neither was edited.

Ruled out: `to_locale()` conversion, locale-directory globbing, and `write_po_file()` path handling. The defect is solely the broad hyphen check in `makemessages.py`.

Conclusion: validation should reject hyphens only in the base language/country segment (e.g. `pl-PL`), while allowing private-use/extension tails such as `x-informal`. Add a regression test for `nl-nl-x-informal`/`nl_NL-x-informal` in `tests/i18n/test_extraction.py`.
