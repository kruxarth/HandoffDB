# Handoff: templates.E003 false positive for libraries in TEMPLATES OPTIONS

## Issue
`check_for_template_tags_with_the_same_name` reports `templates.E003` ("'my_tags' is used for multiple template tag modules: 'someapp.templatetags.my_tags', 'someapp.templatetags.my_tags'") when a library is also declared in `TEMPLATES['OPTIONS']['libraries']`. The same module path appears twice, producing a false positive.

## Relevant code
- `django/core/checks/templates.py:18-21` — `E003` error definition.
- `django/core/checks/templates.py:51` — `check_for_template_tags_with_the_same_name`; it combines libraries from installed-app discovery with those in `TEMPLATES['OPTIONS']['libraries']` and flags names mapping to more than one module path. It does not deduplicate identical module paths, which is the defect.
- `django/template/backends/django.py:88-107` — `get_template_tag_modules()`; yields `(module_name, module_path)` only from `django.templatetags` and each app's `templatetags` package. It does not read `OPTIONS['libraries']`, so it is not the source of the duplicate; the duplicate arises where the check merges both sources.
- `django/template/backends/django.py:110-118` — `get_installed_libraries()`, related helper.

## Tests
`tests/check_framework/test_templates.py` — imports `E003` (line 6) and calls the check at lines 141, 157, 174, 200, 209. A regression test should configure a library in `TEMPLATES['OPTIONS']['libraries']` that is also discoverable via an app's `templatetags` package and assert `[]`.

## Docs
`docs/ref/checks.txt` documents `templates.E003`; update wording if the fix changes semantics.

## Ruled out
- `E003` message construction (line 19) — correct.
- `get_template_tag_modules()` (lines 88-107) — only performs app discovery; not responsible.
- `check_setting_app_dirs_loaders` (line 25) and `check_string_if_invalid_is_string` (line 37) — unrelated checks, unaffected.

## Conclusion
False positive caused by the check listing the same module path twice when a library is both installed-app-discoverable and explicitly configured in `TEMPLATES['OPTIONS']['libraries']`. Fix by deduplicating module paths per library name inside `check_for_template_tags_with_the_same_name` (`django/core/checks/templates.py:51`) before comparing, and add the regression test above.
