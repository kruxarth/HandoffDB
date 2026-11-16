# Handoff: Lazy `__file__` access

**Issue.** Frozen Python environments may not define module `__file__`; Django must not access it at import/class-definition time. Five modules do. This ticket fixes four and defers `trans_real`.

**Files/lines.**
- `django/forms/renderers.py:10` defines undocumented `ROOT = Path(__file__).parent`, used only by `EngineMixin.engine` (~line 39). Remove `ROOT` and build the path lazily.
- `django/utils/version.py:80` inside `get_git_changeset()` derives the repo directory from `__file__`. Return `None` when `__file__` is missing, matching git-failure behavior.
- `django/views/debug.py:29` defines `CURRENT_DIR`, used at lines 251, 255, 537, and 556. Replace it with a private `_builtin_template_path()`. Preserve #32105 overrideability of `ExceptionReporter.html_template_path`/`text_template_path` by setting defaults in `__init__`, not in the class body.
- `django/contrib/auth/password_validation.py:170` defines class constant `DEFAULT_PASSWORD_LIST_PATH`, used as the default argument at line 172. Make it an instance attribute in `__init__` (or a `classproperty` if the signature must remain).

**Tests/docs.** `tests/forms_tests/tests/test_renderers.py`; `tests/version/tests.py` (covers `get_version`, not `get_git_changeset` directly); `tests/view_tests/tests/test_debug.py` and custom reporters in `tests/view_tests/views.py:247-248`; `tests/auth_tests/test_validators.py:185-212`. Docs: `docs/topics/auth/passwords.txt:543,550` documents `CommonPasswordValidator(password_list_path=DEFAULT_PASSWORD_LIST_PATH)`.

**Ruled out.** Removing `__file__` entirely, banning module-level use generally, style-doc updates, broad new tests, and changing `django/utils/translation/trans_real.py:186,426` (deferred to #30950). Test code and undocumented private symbols (`ROOT`, `CURRENT_DIR`) need no deprecation.

**Conclusion.** Implement lazy access in the four modules; leave `trans_real` unchanged.
