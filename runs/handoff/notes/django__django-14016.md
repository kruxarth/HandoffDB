## Handoff: `TypeError: cannot pickle` on `Q() | Q(...)`

**Issue.** `Q() | Q(x__in={}.keys())` raises `TypeError: cannot pickle 'dict_keys' object`. Any unpicklable value used as a `Q` child crashes the `|`/`&` operators when one side is empty.

**Root cause (confirmed).** `Q._combine()` in `django/db/models/query_utils.py:43-58` returns `copy.deepcopy(self)` (line 49) when `self` is empty and `copy.deepcopy(other)` (line 52) when `other` is empty. `__or__`/`__and__` (lines 60-64) route every combination through it. `copy.deepcopy` falls back to pickle for objects like `dict_keys`, hence the traceback. The `Q` was already constructible — `Q.__init__` (line 40) and `tree.Node.__init__` (`django/utils/tree.py:21-25`, which does `children[:]`) are fine; only the copy path breaks.

**Ruled out.** `WhereNode.clone()/copy()` (`django/db/models/sql/where.py:142-163`) is SQL-compilation only and never runs here. `GEOSGeometry.__deepcopy__` (`django/contrib/gis/geos/geometry.py:74-78`) exists *because* `Node` deepcopies; it is a symptom of the same design, not the bug. No other `deepcopy` in `django/` touches `Q` children.

**Conclusion / suggested fix.** The deepcopy is unnecessary — combining only needs a new node owning its own `children` list; children are never mutated in place. Add a `Node.copy()` to `django/utils/tree.py` returning `self._new_instance(self.children, self.connector, self.negated)` (shallow child list via `__init__`), and replace both `copy.deepcopy(...)` calls in `_combine` with `.copy()`. Keep the `conditional` `TypeError` guard.

**Tests.** `tests/queries/test_q.py` (`QTests`: `test_combine_or_empty` 14-17, `test_combine_or_both_empty` 19-20, `test_combine_not_q_object` 22-28) is where to add a regression test using `{}.keys()`. `tests/utils_tests/test_tree.py::test_deepcopy` (68-72) covers existing copy semantics and must keep passing. Docs: `docs/ref/models/querysets.txt`, "Q objects" section. Repo is Django 4.0.0 alpha (`django/__init__.py:3`).
