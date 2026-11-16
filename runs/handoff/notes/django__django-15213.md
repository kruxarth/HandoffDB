# Handoff: ExpressionWrapper(~Q(pk__in=[])) renders empty SQL

## Issue
`qs.annotate(foo=ExpressionWrapper(~Q(pk__in=[]), output_field=BooleanField()))` compiles to `SELECT AS "foo" FROM ...` — an empty SQL fragment instead of a literal. The non-negated `ExpressionWrapper(Q(pk__in=[]))` works and yields `SELECT 0 AS "foo"`.

## Relevant code
- `django/db/models/expressions.py:956-976` — `ExpressionWrapper`. It does not define `empty_result_set_value`, so the compiler has no fallback when the wrapped expression raises `EmptyResultSet`.
- `django/db/models/expressions.py:153` — `BaseExpression.empty_result_set_value = NotImplemented` (the sentinel that suppresses fallback).
- `django/db/models/sql/compiler.py:271-285` — `select` compilation catches `EmptyResultSet`; it substitutes `'0'` only if `empty_result_set_value` is `NotImplemented`, otherwise compiles `Value(value)`.
- `django/db/models/sql/where.py:14-113` — `WhereNode.as_sql`; negated empty nodes emit no SQL, so `ExpressionWrapper.as_sql` returns `('', ())`.
- `django/db/models/lookups.py:388-425` — `In.process_rhs` raising `EmptyResultSet` on empty rhs (correct; not the bug).
- Precedents for the fix: `expressions.py:700-713` (`Func.as_sql`), `expressions.py:1113` (`Case`), `expressions.py:1143` (`Subquery`), `sql/query.py:146` (`Query`).

## Tests / docs
- `tests/annotations/tests.py:200-215` — existing `ExpressionWrapper(Q(pk__in=[]))` coverage; add the negated variant here.
- `tests/expressions/tests.py:2015-2027` — `ExpressionWrapperTests`.
- `tests/queries/tests.py:207-210`, `1635-1650` — empty/negated `Q` semantics.
- `docs/releases/4.1.txt` — no entry yet; add a bugfix note if required.

## Ruled out
`In.process_rhs`/`EmptyResultSet` raising, `Q.__invert__` (`query_utils.py:65`), and the compiler's `'0'` fallback are all behaving correctly; the gap is `ExpressionWrapper` not forwarding `empty_result_set_value`.

## Conclusion
Give `ExpressionWrapper` an `empty_result_set_value` property that delegates to `self.expression.empty_result_set_value` (returning `NotImplemented` when the inner expression has none), so `compiler.select` emits a valid literal for negated empty `Q`. Add a regression test in `tests/annotations/tests.py`.
