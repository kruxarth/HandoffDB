# Handoff: `RenameIndex` unnamed-index reversal

**Issue:** `RenameIndex(..., old_fields=...)` for an auto-named `index_together`/`unique_together` index crashes when re-applied after `database_backwards()`. PostgreSQL reports `relation "new_pony_test_idx" already exists`.

**Code paths:** `django/db/migrations/operations/models.py:879` defines `RenameIndex`; init/deconstruct are `879-914`. The `old_fields` branch in `state_forwards` is `916-922`. `database_forwards` handles `old_fields` around `923-953`: it reconstructs the auto-generated old name via `models.Index(fields=self.old_fields).set_name_with_model(...)` and renames it to `new_name`. The matching `database_backwards` `old_fields` branch returns early as a no-op (near `955`; confirmed by `assertNumQueries(0)` in the test), leaving `new_name` in place. Supporting code: `django/db/backends/base/schema.py:496-503` (`rename_index`), `:1375-1382` (`_rename_index_sql`), `:1259-1288` (`_create_index_name`), and `django/db/migrations/state.py:214-222`.

**Tests/docs:** `tests/migrations/test_operations.py:2964-2994` (`test_rename_index_unnamed_index`); named-index test `2903-2949`; argument test `2951-2963`. Docs: `docs/ref/migration-operations.txt:225-238`; release note `docs/releases/4.1.txt:348`.

**Ruled out:** backend rename SQL and `can_rename_index` feature handling; `state_forwards`; PostgreSQL-specific backend bug. The auto-generated name is not stored on the operation and must be recomputed.

**Conclusion:** Fix `RenameIndex.database_backwards` for `old_fields`: do not no-op. Reconstruct the auto-named old index with `Index(fields=self.old_fields).set_name_with_model(model)` and call `schema_editor.rename_index(model, new_index, old_index)`. Then backward restores the auto name and re-forward succeeds. Update the test to assert the old auto name exists after backward before re-applying.
