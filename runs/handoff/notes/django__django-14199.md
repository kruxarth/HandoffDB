# Handoff note: `Value()` + `DecimalField` crash on SQLite

## Issue
`SomeModel.objects.all().annotate(x=Value(1, output_field=DecimalField()))` raises `TypeError: argument must be a float` on SQLite: the string `'1'` returned by the database is passed to `create_decimal_from_float`.

## Key files/lines
- `django/db/backends/sqlite3/operations.py:307-320` — `get_decimalfield_converter()` is the culprit. Line 310 sets `create_decimal = decimal.Context(prec=15).create_decimal_from_float`, which only accepts floats. Registered at lines 279-280 in `get_converters()` for `DecimalField` expressions.
- `django/db/backends/sqlite3/base.py:79` — `Database.register_adapter(decimal.Decimal, str)` explains why Decimal params round-trip as strings.
- `django/db/models/expressions.py:710-755` — `Value`; `as_sql()` calls `output_field.get_db_prep_value()`.
- `django/db/models/fields/__init__.py:1545-1552` — `DecimalField.get_db_prep_value()`: uses `create_decimal_from_float` only for floats, otherwise `decimal.Decimal(value)`; handles ints/strings fine.
- `django/db/models/expressions.py:326-329` — `Expression.convert_value` already uses `Decimal(value)`, which accepts strings.

## Ruled out
`Value.as_sql`, `get_db_prep_value`, and the generic `convert_value` path are all string-safe; the failure is isolated to the SQLite backend converter.

## Conclusion / fix
In `get_decimalfield_converter()`, when the expression is a `Value` (import it from `django.db.models.expressions`), use `decimal.Context(prec=15).create_decimal` (string/Decimal-capable) instead of `create_decimal_from_float`. Keep the float path for column/aggregate expressions, where 15-digit truncation matters.

## Tests/docs
Regression test belongs in `tests/expressions/tests.py`, class `ValueTests` (~line 1702), e.g. annotate a `DecimalField` value and compare; `tests/expressions/models.py` currently has no decimal model, so reuse `Company`/`Number` or add one. Related coverage: `tests/expressions/tests.py:1770`, `tests/annotations/tests.py:156`. Update `docs/ref/models/expressions.txt` (`Value`) only if behavior is documented.
