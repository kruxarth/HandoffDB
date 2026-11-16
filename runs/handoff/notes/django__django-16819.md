## Handoff: Reduce Add/RemoveIndex migration operations

**Issue:** MigrationOptimizer should collapse redundant `AddIndex`/`RemoveIndex` (and `AddConstraint`/`RemoveConstraint`) operations, e.g. add-then-remove of the same index should optimize to nothing.

**Where it matters:**
- `django/db/migrations/operations/models.py:811-864` (`AddIndex`) and `:865-~895` (`RemoveIndex`): neither defines `reduce()`, so the optimizer treats them as opaque boundaries. `AddConstraint`/`RemoveConstraint` similarly lack `reduce()`. This is the core gap.
- `django/db/migrations/operations/base.py:129` — `Operation.reduce()` base returns `None`; existing reducers in `operations/fields.py:69-354` show the pattern to follow.
- `django/db/migrations/optimizer.py` (69 lines) — calls `reduce()` in its forward-scan loop; no changes needed here, only operations need reducers.
- `django/db/migrations/autodetector.py:1305-1400` — generates these ops; not the fix location.

**Tests/docs:** `tests/migrations/test_optimizer.py` (only `RenameIndex` cases at lines 1127-1156; add Add/RemoveIndex + constraint optimization cases). Docs: `docs/ref/migration-operations.txt:229-266`. Postgres subclass tests: `tests/postgres_tests/test_operations.py`.

**Ruled out:** `django/contrib/postgres/operations.py:119-176,259-330` — `AddIndexConcurrently`/`RemoveIndexConcurrently` subclass `AddIndex`/`RemoveIndex`; fixing base classes covers them. `django/db/migrations/state.py:214-240` add/remove/rename helpers exist and are unrelated to reduce logic.

**Conclusion:** The operations were never given `reduce()` implementations. Add `reduce()` to `AddIndex`, `RemoveIndex`, `AddConstraint`, `RemoveConstraint` so that an add followed by a remove of the same name cancels to nothing (and same-model ops don't wrongly cancel across different index names), then cover with optimizer tests.
