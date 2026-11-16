## Handoff: `makemigrations --noinput` silent abort

**Issue:** `--noinput` suppresses prompts but also produces no diagnostic when `makemigrations` aborts because developer input was required. Scripts cannot distinguish this from success. Desired behavior is a warning (stdout/stderr) such as “No migrations run because input was required but --noinput option was specified.”

**Key files/lines:**
- `django/core/management/commands/makemigrations.py`
  - L45: `--noinput` sets `interactive=False`.
  - L147–149: selects `InteractiveMigrationQuestioner` vs `NonInteractiveMigrationQuestioner`; L149 is where verbosity/output must be passed.
  - L248–250: merge-path questioner selection; also needs output wiring.
- `django/db/migrations/questioner.py`
  - L14: base `MigrationQuestioner`.
  - L260–272: `NonInteractiveMigrationQuestioner`; its `sys.exit(3)` paths are the abort points that must emit the warning.
  - L89–256: interactive questioner exit paths; these are expected prompt behavior, not the target.
- `django/core/management/commands/migrate.py` L40: also defines `--noinput`, but no questioner/prompt path was found; likely no change needed there.

**Tests:**
- `tests/migrations/test_commands.py` L1350–1364 (`non_interactive_not_null_addition`), L1407–1422 (`non_interactive_not_null_alteration`), L1469–1499 (rename cases), L1505+ (merge `--noinput`). These currently assert `SystemExit`/success but not warning text.
- `tests/migrations/test_questioner.py` covers questioner behavior and is the place for unit-level assertions.
- Docs: `docs/ref/django-admin.txt` (`makemigrations`/`migrate` options) and `docs/topics/migrations.txt`; not yet inspected.

**Ruled out:** `migrate.py` prompt handling; changing interactive questioner exits; treating `--noinput` as failure by exit code alone.

**Conclusion:** Add an output/verbosity channel to `NonInteractiveMigrationQuestioner`, emit a clear warning before each `sys.exit(3)`, and pass it from `makemigrations` at L149/L250. Update tests to assert the warning alongside `SystemExit`.
