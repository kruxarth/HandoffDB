## Handoff: Deprecate `Meta.index_together`

**Issue:** Deprecate `Model.Meta.index_together` in favor of `Meta.indexes` / `Index`, since `indexes` can express everything `index_together` can.

**Key code paths**
- `django/db/models/options.py:43,116,202` — `index_together` is a recognized Meta option, initialized and normalized here. This is the primary deprecation point.
- `django/db/models/base.py:1550,1845-1872` — model system checks for `index_together`; warning/validation should account for this path.
- `django/db/migrations/state.py:315,810-811,828` — migration state preserves and renders `index_together`.
- `django/db/migrations/operations/models.py:598-616` — `AlterIndexTogether` operation; also `:240-256` handles `RemoveField` cleanup.
- `django/db/migrations/autodetector.py:192,199,1480+` — generates alter/remove operations for `index_together`.
- `django/db/backends/base/schema.py:542-549,1406-1414` and `django/db/backends/sqlite3/schema.py:274-319` — schema editor still consumes `_meta.index_together`; cannot remove yet.

**Tests/docs**
- `tests/indexes/tests.py:82-93`
- `tests/invalid_models_tests/test_models.py:31-132` (`IndexTogetherTests`)
- `tests/migrations/test_autodetector.py:4592-4766`
- `tests/migrations/test_operations.py`, `tests/migrations/test_state.py:49,143`, `tests/migrations/test_base.py:258-266`
- `tests/schema/tests.py:2891-2982`
- `docs/ref/models/options.txt`; `docs/releases/4.2.txt:273-284`

**Ruled out:** No existing deprecation warning in models/migrations for this option; no `RemovedInDjango51Warning` usage in these paths. `tests/runtests.py:46-47` treats `RemovedInDjango50Warning`/`RemovedInDjango51Warning` as errors, so tests must be updated or explicitly catch the new warning.

**Conclusion:** Add a `RemovedInDjango51Warning` when `Meta.index_together` is used, while retaining migration operations and backend support until removal. Update the listed tests and 4.2 deprecation docs. No code changes were made in this investigation.
