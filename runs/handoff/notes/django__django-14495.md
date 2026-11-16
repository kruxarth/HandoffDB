# Handoff: KeyError when migrating back to a replaced (squashed) migration

## Issue
With `0001_initial.py`, `0002_thing_age.py`, and `0001_squashed_0002.py` all on disk, `migrate app 0001` fails with "More than one migration matches '0001'", yet `migrate app 0001_initial` crashes with `KeyError: ('app', '0001_initial')`.

## Where it breaks
- `django/db/migrations/executor.py:50` (`MigrationExecutor.migration_plan`) indexes `self.loader.graph.node_map[target]` with no membership check. Replaced migrations are not graph nodes because `build_graph()` drops them — that is the KeyError.
- `django/db/migrations/loader.py`, `get_migration_by_prefix()` (later in the class, after `build_graph()`, roughly lines 300–360) matches against all disk migrations, including replaced ones — hence the false ambiguity.
- `django/core/management/commands/migrate.py:130-140` calls `get_migration_by_prefix()` and then `migration_plan()`; `django/core/management/commands/sqlmigrate.py` follows the same pattern.
- `django/db/migrations/graph.py` (`add_node`/`node_map`) only ever holds replacement nodes.

## Tests and fixtures
Fixture: `tests/migrations/test_migrations_squashed/` (`0001_initial.py`, `0002_second.py`, `0001_squashed_0002.py`). Relevant tests: `tests/migrations/test_loader.py:249` (`test_loading_squashed`); `tests/migrations/test_executor.py:615-660` (#24628, replaced migrations already applied); `tests/migrations/test_commands.py:818` (`test_sqlmigrate_replaced_migration`), `~839` (`test_sqlmigrate_ambiguous_prefix_squashed_migrations`, which asserts today's ambiguity error and must change), `:902` (`test_migrate_record_replaced`).

## Ruled out
The loader's replacement-consistency error path (`loader.py:260-290`, #23556) is unrelated. Only this checkout's Django (4.0 alpha) is available; there is no installed copy to compare against.

## Conclusion
Preferred fix: resolve targets through `loader.replacements` so a replaced migration is reachable and rollback into a squashed set works. Otherwise, exclude replaced migrations from prefix matching and raise `NodeNotFoundError`/`CommandError` rather than a bare KeyError. Docs: `docs/topics/migrations.txt:625-690`; release-note slot at `docs/releases/4.0.txt:277`.
