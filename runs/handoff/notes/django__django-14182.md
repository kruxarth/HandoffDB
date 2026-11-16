## Handoff: precision argument for `Round`

**Issue:** `Round` only rounds to the nearest integer. All natively supported backends (Postgres, SQLite, MySQL, Oracle) accept a second `ROUND(x, n)` argument, so Django should expose a `precision` parameter.

**Code that matters:**
- `django/db/models/functions/math.py:161-163` — `class Round(Transform)` with `function = 'ROUND'`, `lookup_name = 'round'`. This is the only place to change.
- `django/db/models/lookups.py:158-164` — `Transform` sets `arity = 1`; `Round` must override this or passing two expressions raises `TypeError`.
- `django/db/models/expressions.py:636-658` — `Func.__init__` enforces `arity` and parses positional expressions; the default template renders them comma-separated, so no custom `as_sql` is needed.
- `django/db/models/functions/__init__.py:13,37` — `Round` export; unchanged unless renaming.

**Tests/docs:**
- `tests/db_functions/math/test_round.py` — existing null/decimal/float/integer tests; add cases asserting `Round('field', 2)` output for decimal/float/integer and a default-precision regression.
- `docs/ref/models/database-functions.txt:1147-1167` — `Round` docs; update signature/examples to document `precision` (default 0) and lookup registration.

**Ruled out:** Backend-specific overrides. `django/db/backends/*/functions.py` only contains `oracle/functions.py` (`IntervalToSeconds`, `SecondsToInterval`), with no `Round`. Grepping `django/db/backends/` found no `ROUND` handling (only decimal `Rounded` traps and Oracle date comments). Therefore no `as_postgres`/`as_sqlite`/`as_mysql`/`as_oracle` methods are required.

**Conclusion:** Give `Round` `arity = 2` and `__init__(self, expression, precision=0)` forwarding `expression, precision` to `super().__init__`. Keep `Transform` inheritance and default precision `0` for backward compatibility. Repo is Django 4.0 alpha at commit `38f6726`.
