# Handoff: `Q.deconstruct()` crashes on non-subscriptable children

**Issue:** `Q.deconstruct()` special-cases single-child Q objects, treating the child as a `(key, value)` pair and emitting it as kwargs. For `Q(Exists(...))`, the child is an `Exists` expression, not a subscriptable tuple, so `child[0]` raises `TypeError`. Multi-child Q objects already deconstruct children into `args`.

**Key code:** `django/db/models/query_utils.py` — `Q` class starts around line 23; `Q.__init__` around lines 36-37 builds `children` from `args` plus sorted kwargs; `Q.deconstruct()` at line 83. The faulty single-child branch is around lines 89-92, with the crash at line 90 (`kwargs = {child[0]: child[1]}`). Removing that branch makes all children deconstruct through `args`.

**Tests/docs:** `tests/queries/test_q.py`, class `QTests`; deconstruct tests at lines 38-112. Existing assertions (`test_deconstruct`, negated/or/and/nested/multiple-kwargs) currently expect single-child kwargs Qs to produce empty `args` and populated `kwargs`; they must be updated to expect `args=(('key', value),)` and `kwargs={}`. Add a regression test deconstructing `Q(Exists(...))` (or another non-subscriptable expression). Relevant docs: `docs/ref/models/querysets.txt` (Q object reference); this deconstruct behavior is undocumented.

**Ruled out:** The bug is not in `Exists` or expression construction. Searches found no existing tests covering single-child `Q(...).deconstruct()` or `Q(Exists(...))` deconstruction. Keeping the special case via an explicit “length-2 tuple” check is possible but preserves undocumented behavior.

**Conclusion:** Adopt PR 14126’s approach: delete the single-child special case so single-child Q objects deconstruct into `args`, and update/add tests in `tests/queries/test_q.py`.
