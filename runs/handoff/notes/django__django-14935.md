# Handoff: makemigrations warning for unique fields with callable defaults

**Issue:** A callable field default is serialized into an `AddField` migration and evaluated once during migration, so existing rows can all receive the same value. Requested behavior: `makemigrations` should warn when a unique field uses a callable default.

**Files/lines that matter:**
- `django/db/migrations/autodetector.py:856-889` — `_generate_added_field()` builds `AddField`; `preserve_default` logic is at `869-889`. This is where field metadata (`unique`, `default`, callable) is available.
- `django/core/management/commands/makemigrations.py:3,108` — already imports `warnings` and emits warnings; likely place for user-facing warning.
- `django/db/migrations/questioner.py:13-...` — handles migration prompts/defaults, but has no warning hook.

**Tests/docs:** `tests/migrations/test_autodetector.py` covers added fields and `unique_together`, but no callable-default warning test. `tests/migrations/test_questioner.py` covers questioner behavior only. Docs to update if warning behavior is documented: `docs/topics/migrations.txt` and `docs/ref/django-admin.txt`.

**Ruled out:** No existing callable-default/unique warning in `django/db/migrations`; `operations/special.py:143-151` only validates `RunPython` callables. `tests/backends/base/test_schema.py` confirms `effective_default()` should not call callable defaults. No existing test covers this case.

**Conclusion:** No fix was implemented in this session. Add the warning around added-field generation or the `makemigrations` command, restricted to unique fields with callable defaults, with tests in `test_autodetector.py`/`test_commands.py` and a docs update.
