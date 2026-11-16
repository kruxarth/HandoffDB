## Handoff: `makemigrations --update`

**Issue:** Add a `--update` flag to `makemigrations`, mimicking South’s `schemamigration --update`, so iterative development can refine the latest migration instead of creating a new one.

**Relevant code**
- `django/core/management/commands/makemigrations.py:27-37` defines command arguments; a new `--update` option belongs here. The `handle()` flow (not fully inspected) will need branching so the latest migration is replaced rather than appended.
- `django/db/migrations/autodetector.py:40-50` (`changes()`) and `1639-1689` (`arrange_for_graph()`) control naming/dependencies against graph leaves; `--update` must target the existing leaf migration and avoid creating a new leaf.
- `django/db/migrations/loader.py:219-275` (`build_graph()`) and `354-366` (`project_state()`) load migration state; update logic needs the state *before* the latest migration.
- `django/db/migrations/graph.py:314-333` (`make_state()`) and `leaf_nodes()` are needed to derive prior state and identify the migration to replace.
- `django/db/migrations/migration.py:53-60` shows migration fields (`name`, `dependencies`, `operations`) relevant to rewriting a migration file.

**Tests/docs**
- `tests/migrations/test_commands.py` is the command test suite; add coverage for updating latest migration, multiple apps, `--dry-run`, and no-latest-migration errors.
- `docs/ref/django-admin.txt:776-840` documents `makemigrations` options; add `--update`.
- `docs/releases/4.2.txt` is the current release-notes file for a feature note.

**Ruled out:** Grep found no existing `--update`, `handle_update`, or `last_migration` support in `django/` or `tests/`; docs contain no existing equivalent. South-style update behavior is not already implemented.

**Conclusion:** This is a missing feature. Implementing it requires command-option plumbing plus autodetector/loader/graph changes to compute the pre-latest state, replace the leaf migration, and preserve dependencies. No code changes were made in this session.
