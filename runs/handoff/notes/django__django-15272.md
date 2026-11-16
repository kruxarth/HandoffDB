# Handoff: `optimizemigration` management command

## Issue
Add a management command `optimizemigration app_label migration_name` that loads a single migration, runs its operations through `MigrationOptimizer`, and rewrites the result to disk (ignoring squashed-ness, unlike `squashmigrations`).

## State
No implementation exists. `grep -rn "optimizemigration"` over `django/`, `tests/`, `docs/` returns nothing; `find` for any `optimizemigration*` file returns nothing; `git status` is clean. Only `django/db/migrations/autodetector.py:395 _optimize_migrations` matches the name and is unrelated (internal autodetector logic).

## Files that matter
- `django/core/management/commands/squashmigrations.py` — the model to copy: argument parsing (`--no-optimize` pattern), `include_header` option at lines 57/70, `MigrationWriter(new_migration, include_header)` at line 217, `run_formatters([writer.path])` at line 224.
- `django/db/migrations/optimizer.py` — `MigrationOptimizer.optimize(operations, app_label)`; `app_label` is required (raises `TypeError` if `None`).
- `django/db/migrations/writer.py` — `MigrationWriter.__init__` line 124 (`include_header=True`), `as_string` line 129.
- `django/db/migrations/loader.py:145 get_migration_by_prefix` and `django/db/migrations/exceptions.py:4 AmbiguityError` — for resolving the migration name and error reporting.
- `django/core/management/commands/makemigrations.py` lines 64, 101, 253, 292 — same writer/formatter pattern.

## Tests and docs
- `tests/migrations/test_commands.py`: add an `OptimizeMigrationTests` class next to `SquashMigrationsTests` (starts ~line 2529); reuse `MigrationTestBase.temporary_migration_module` (line 1144 region) and `call_command` with `stdout=io.StringIO()`.
- Related: `tests/migrations/test_optimizer.py`, `tests/migrations/test_writer.py`.
- Docs: `docs/ref/django-admin.txt` (no `optimizemigration` entry yet).

## Conclusion
Create `django/core/management/commands/optimizemigration.py` mirroring `squashmigrations.py`, using `MigrationLoader.get_migration_by_prefix`, `MigrationOptimizer.optimize(..., app_label)`, and `MigrationWriter` + `run_formatters`; then add the command test and docs entry.
