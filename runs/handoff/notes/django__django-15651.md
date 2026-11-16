## Handoff: RenameIndex backwards-compatible implementation

**Issue:** Implement `RenameIndex(model, new_name, old_name=None, old_fields=None)` so unnamed/legacy indexes (especially `index_together`) can be renamed, with DB rename where supported and field-based lookup otherwise; autodetector should emit `RenameIndex` instead of drop/add.

**Key files/lines:**
- `django/db/migrations/operations/models.py:879-960` — `RenameIndex`; argument validation at 885-890; `old_fields` lookup via `_constraint_names()` and wrong-count error at 944-958. Backwards rename of unnamed indexes is a no-op.
- `django/db/migrations/autodetector.py:1180-1228` — `create_altered_indexes()` detects renamed `Meta.indexes` by deconstructed equality ignoring name.
- `django/db/migrations/autodetector.py:1252-1265` — `generate_renamed_indexes()` emits `RenameIndex`; called from `_generate_altered_indexes` flow at 175/182.
- `django/db/migrations/state.py:220-233` — `ProjectState.rename_index()`.
- `django/db/backends/base/schema.py:496-501` — `rename_index()` uses `RENAME INDEX` when `can_rename_index`, else drop/create.
- `django/db/backends/base/features.py:180` and `django/db/backends/mysql/features.py:348-354` — feature flag, MySQL/MariaDB version gates.

**Tests/docs:** `tests/migrations/test_operations.py:2903-3066`; `tests/migrations/test_autodetector.py:2568-2590`; `tests/migrations/test_optimizer.py:1112-1140`. Docs: `docs/ref/migration-operations.txt:225-235`, `docs/releases/4.1.txt:348-356`.

**Ruled out:** `AmbiguityError` is not used for ambiguous field-based index lookup; current code raises “Found wrong number…” from `models.py:949`. Autodetector does not bridge `index_together` removals to named `Meta.indexes` additions; it only compares `Meta.indexes`.

**Conclusion:** Core `RenameIndex` and `Meta.indexes` rename autodetection are implemented and tested. Remaining gap is autodetecting `index_together` → named `Meta.indexes` as `RenameIndex` and using `AmbiguityError` for multiple matching indexes.
