# Handoff: Improve reverse accessor clash error messages

## Issue
`RelatedField._check_clashes()` reports reverse accessor/query-name clashes without clearly stating the clashing name, making debugging slow. Reference PR: django/django#14880. Goal: include the clashing field/accessor name in the error messages.

## Key code
- `django/db/models/fields/related.py` — `_check_clashes()` starts at line 198. The clash error strings (fields.E302–E305) are constructed around **lines 250–290**; the reverse-accessor message is at **line 274** (`"Reverse accessor for '%s' clashes with reverse accessor for '%s'."`). Review every branch (E302/E303/E304/E305) since several messages may omit the offending name. `_check_clashes()` is invoked from `_check_related_fields`-style checks at **line 117**.

## Tests
- `tests/invalid_models_tests/test_relative_fields.py` — clash assertions at **lines ~840–1210** (e.g. `_test_accessor_clash` at 853, `_test_reverse_query_name_clash` at 992, explicit-related-query-name clash at 1186). These `Error(...)` string comparisons will need updating.
- `tests/model_inheritance/test_abstract_inheritance.py` — **lines 280–320** assert `fields.E302`/`E303` messages for inherited fields.

## Docs
- `docs/ref/checks.txt` — **lines 250–257** document `fields.E302`–`E305` message formats; update if wording changes.
- `docs/topics/db/models.txt` — line 1179 shows a sample clash message.

## Ruled out / notes
- Repo is a snapshot (commit `3ffbe13`), Django **4.1.0 alpha**; no changes were made this session.
- `--include=*.py` greps failed under zsh; use the `grep` tool instead.
- The clash name is already threaded through `clash_name`/`field_name`; the fix is message wording plus test/doc updates, not new plumbing.

## Conclusion
Fix belongs in `related.py::_check_clashes` (~198–290). No patch applied yet; next agent should edit messages, then update the two test files and `docs/ref/checks.txt`, and run `tests/invalid_models_tests` + `tests/model_inheritance`.
