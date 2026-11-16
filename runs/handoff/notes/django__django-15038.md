**Handoff note**

Issue: `squashmigrations --squashed-name initial myapp 0002` can generate `0001_initial.py`, silently overwriting an existing migration. If already applied, this corrupts code/DB consistency and can add a `replaces` entry causing `CircularDependencyError`. The command should fail instead of overwriting.

Key files:
- `django/core/management/commands/squashmigrations.py`: `add_arguments()` at lines 13–41 defines `--squashed-name`; `handle()` later selects the output migration name and writes via `MigrationWriter` (around lines 120–170). This write path lacks an existence check.
- `tests/migrations/test_commands.py`: `SquashMigrationsTests` starts around line 1975. Existing `--squashed-name` coverage is at lines 2063–2082 (`test_squashed_name_with_start_migration_name`, `test_squashed_name_without_start_migration_name`) and only checks successful creation, not collisions.
- Docs: `docs/ref/django-admin.txt` documents `squashmigrations` and `--squashed-name`; update it to state existing files are not overwritten.

Ruled out: migration loader/optimizer behavior and `makemigrations`’ `__init__.py` check (`django/core/management/commands/makemigrations.py:231`) are unrelated. The defect is the missing output-file guard in `squashmigrations`.

Conclusion: Before writing the squashed migration, check `os.path.exists(writer.path)` and raise `CommandError` explaining that the target migration already exists. Add a regression test using `--squashed-name initial` where `0001_initial.py` already exists, asserting `CommandError` and unchanged file contents. Also test that the circular dependency scenario is prevented by failing early.
