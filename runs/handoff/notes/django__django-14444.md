# Handoff: SQLite covering/deferrable UniqueConstraint noop

**Issue.** On SQLite, `UniqueConstraint(fields=['name'], name='name_unq_covering', include=['weight'])` emits `models.W039` ("A constraint won't be created") but a unique index *is* still created — the `INCLUDE` columns are silently dropped. The warning is therefore misleading; covering and deferrable unique constraints should be true noops on SQLite.

**Key code.**
- `django/db/backends/base/schema.py:1191-1215` — `_unique_sql()`: deferrable already returns `None` when unsupported, but `include`/`opclasses` fall through to `_create_unique_sql()`, which builds a `CREATE UNIQUE INDEX` without INCLUDE.
- `django/db/backends/base/schema.py:1014-1058` — `_index_include_sql()` / `_create_unique_sql()`: silently drop INCLUDE when `supports_covering_indexes` is False.
- `django/db/backends/sqlite3/schema.py:421-433` — `add_constraint()` / `remove_constraint()`: only condition/expression constraints use `super()`; everything else calls `_remake_table()`, so covering/deferrable constraints still rebuild the table.
- `django/db/backends/base/features.py:26,283` and `django/db/backends/sqlite3/features.py` — `supports_deferrable_unique_constraints` / `supports_covering_indexes` are False.
- `django/db/models/base.py:2029-2060` — W039 emission (correct; leave alone).

**Tests/docs.** `tests/invalid_models_tests/test_models.py:2114-2170` (W039), `:1989-2025` (W038); `tests/schema/tests.py:2329-2370` (`test_func_unique_constraint_covering`), `:2204-2240` (`test_unique_constraint`); `tests/migrations/test_operations.py:395-440`, `:2380-2420`. Docs: `docs/ref/models/constraints.rst`, `docs/ref/databases.txt` (SQLite), `docs/ref/checks.txt`.

**Ruled out.** Feature flags should not be flipped; expression/condition handling already works via `super()`; the W039 check itself is correct.

**Conclusion.** Make `_unique_sql()` return `None` when `include`/`opclasses` are set and the feature is unsupported, and make SQLite `add_constraint()`/`remove_constraint()` skip `_remake_table()` for these constraints, so no index or table rebuild occurs.
