## Handoff: DecimalField `Case()`/`ExpressionWrapper()` on SQLite

**Issue:** On SQLite, filtering against a `DecimalField` annotation wrapped in `ExpressionWrapper()` or `Case()`/`When()` compares the generated SQL expression as text/integer affinity rather than numeric, so `x__gt=0` fails. Direct field comparisons and plain `Value(..., output_field=DecimalField())` work.

**Key code:**
- `django/db/models/expressions.py:18-29` — `SQLiteNumericMixin.as_sqlite()` casts `DecimalField` expressions to `CAST(... AS NUMERIC)`. It is mixed into `CombinedExpression` (`:445`), `Func` (`:654`), `Value` (`:734`), and `Window` (`:1289`), but **not** `ExpressionWrapper` (`:936-966`) or `Case` (`:1035+`) / `When` (`:968+`).
- `ExpressionWrapper.as_sql()` (`:960-961`) only compiles the inner expression, so the `DecimalField` output type is lost for SQLite casting.
- `Case.as_sql()` uses `connection.ops.unification_cast_sql()` around `:1107`; the base implementation returns `'%s'` (`django/db/backends/base/operations.py:93-100`), and SQLite does not override it, so no numeric cast occurs.
- SQLite conversion/adaptation: `django/db/backends/sqlite3/operations.py:286-327` (`get_decimalfield_converter`, decimal conversion) and `django/db/backends/base/operations.py:487-488,521-524` (`adapt_decimalfield_value`).

**Tests/docs:** Add regression coverage in `tests/model_fields/test_decimalfield.py` using `Foo` from `tests/model_fields/models.py` (`a`, `d`). Related expression tests are in `tests/expressions/tests.py`; docs for these expressions are in `docs/ref/models/expressions.txt`.

**Ruled out:** Direct `d__gt=0` filtering and plain `Value(DecimalField)` annotations already work; the DB converter/adaptation path is not the primary cause. The failure is SQL generation for wrapped/case expressions.

**Conclusion:** SQLite needs the `SQLiteNumericMixin` numeric cast for `ExpressionWrapper` and `Case` when their `output_field` is `DecimalField`, likely by mixing it in or explicitly casting in `as_sqlite()`.
