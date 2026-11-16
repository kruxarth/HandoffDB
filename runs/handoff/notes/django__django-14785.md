## Handoff: SQLite DecimalField NaN retrieval

**Issue:** A `DecimalField` can store `NaN` in SQLite (as text), but fetching the row raises `TypeError: argument must be int or float`. This also breaks admin change/changelist views.

**Key code:** `django/db/backends/sqlite3/operations.py`, `get_decimalfield_converter()` lines 314–327. Line 317 sets `create_decimal = decimal.Context(prec=15).create_decimal_from_float`; converters at lines 321–323 and 325–327 call it. SQLite returns the stored value as the string `'NaN'`, which `create_decimal_from_float()` rejects. Use the context’s `create_decimal()` instead, which accepts both floats and string NaN/Infinity representations, preserving existing float rounding behavior.

Related storage behavior: `django/db/backends/sqlite3/base.py` line 79 registers `decimal.Decimal` adapter as `str`, and line 96 maps `DecimalField` to `decimal`.

**Tests:** `tests/model_fields/test_decimalfield.py` (existing `DecimalFieldTests`, lines 11–102; `test_fetch_from_db_without_float_rounding` near line 95) is the natural regression location. `tests/model_fields/models.py` lines 22–24 define `Foo.d = DecimalField(max_digits=5, decimal_places=3)`. SQLite backend operation tests live in `tests/backends/sqlite/test_operations.py`.

**Docs:** `docs/ref/models/fields.txt` (`DecimalField`) and `docs/ref/databases.txt` (SQLite notes); add a release note if behavior changes.

**Ruled out:** `DecimalValidator` (`django/core/validators.py` lines 397+) already rejects NaN via exponent checks, so form validation is not the failure. `format_number()` in `django/db/backends/utils.py` lines 224–239 is not on the retrieval path. `DecimalField.to_python()`/`get_db_prep_value()` are not the cause; the failure is purely the SQLite result converter.

**Conclusion:** Replace `create_decimal_from_float` with `Context.create_decimal` in the SQLite converter and add a regression test storing/refreshing `float('nan')`.
