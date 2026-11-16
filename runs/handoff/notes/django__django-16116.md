## Handoff: `makemigrations --check` writes migrations

**Issue:** `makemigrations --check` currently writes migration files before exiting non-zero when changes are detected. It should only detect/report changes and exit, matching `migrate --check` and `optimizemigration --check`. Users should not need `--dry-run` to avoid file creation.

**Key code**
- `django/core/management/commands/makemigrations.py`
  - `--check` argument: lines 70-73; read into `check_changes` at line 113.
  - `handle()` branch at line 255 calls `sys.exit(1)` after the write path, so files are already created.
  - `write_migration_files()` lines 330-388 writes unless `self.dry_run` (around line 363).
- Reference behavior, do not change:
  - `django/core/management/commands/migrate.py:257-262` exits on `--check` without applying.
  - `django/core/management/commands/optimizemigration.py:75` returns on `--check` without writing.

**Tests**
- `tests/migrations/test_commands.py:2389-2403` (`test_makemigrations_check`) only asserts exit status; extend it to assert no migration file is created.
- Related dry-run coverage: lines 2033-2072 and 2095-2134.
- `optimizemigration --check` test: lines 3151-3154.

**Docs**
- `docs/ref/django-admin.txt:823` documents `makemigrations --check`; clarify it does not write migrations.
- `docs/releases/1.10.txt:332` introduced the option; `docs/releases/4.2.txt` Management Commands section around lines 194-198 may need a release note for the behavior change.

**Ruled out:** Changing `migrate`/`optimizemigration`; requiring `--dry-run`; altering dry-run/merge behavior.

**Conclusion:** Move the `check_changes` exit before `write_migration_files()`/update handling, preserving change reporting, then update tests and docs.
