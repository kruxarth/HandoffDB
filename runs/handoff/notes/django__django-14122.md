# Handoff Note

## Issue
`Meta.ordering` fields are still added to the `GROUP BY` clause when aggregating, producing wrong aggregation results. Commit `0ddb4ebf` removed the `ORDER BY` for `Meta.ordering`, but `get_group_by()` still receives and uses those ordering expressions. Ticket #14357 (closed), follow-up PR #14122.

## Key code
- `django/db/models/sql/compiler.py`
  - `__init__` ~line 41: `self._meta_ordering = None` flag.
  - `pre_sql_setup()` ~lines 50–60: calls `order_by = self.get_order_by()` then `get_group_by(self.select + extra_select, order_by)` — the ordering list is passed straight into `GROUP BY`.
  - `get_group_by()` line 63: builds `GROUP BY` cols from `select` + `order_by`.
  - `get_order_by()` line 271: falls through to `self.query.get_meta().ordering` (Meta ordering) when no explicit ordering exists.
  - `as_sql()` ~line 600–615: uses `self._meta_ordering` around `GROUP BY`/ordering handling.

## Tests
- `tests/aggregation/tests.py`: `test_aggregation_random_ordering` (line 1329) confirms `Random()` ordering is excluded from `GROUP BY`; subquery-in-GROUP-BY tests at lines 424/435, 1136, 1218.
- `tests/aggregation_regress/tests.py` line 745–747: single `GROUP BY` clause check (#15709); line 192 "Implicit ordering is also ignored".
- `tests/aggregation_regress/models.py` lines 38–39: `Book.Meta.ordering = ('name',)` — the model to reproduce against.
- `tests/queries/models.py` `Tag` (`ordering=['name']`); `tests/queries/tests.py:1969` `test_annotated_default_ordering`.
- `tests/ordering/models.py` / `tests/ordering/tests.py:459` (F expressions in Meta.ordering).

## Ruled out
`Random()` ordering is already excluded from `GROUP BY`, so the fix must target the `_meta_ordering` path in `pre_sql_setup`/`get_group_by`, not general ordering. No existing test exercises `Meta.ordering` + `annotate`.

## Conclusion
Ordering expressions originating from `Meta.ordering` must be stripped from the `order_by` list before it is passed to `get_group_by()` (mirroring the `Random()` exclusion), so they no longer widen `GROUP BY`. Add a regression test in `tests/aggregation/tests.py` using a model with `Meta.ordering`.
