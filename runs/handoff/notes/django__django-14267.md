## Handoff: Q() deconstruct crash with non-subscriptable children

**Issue:** `Q(Exists(...)).deconstruct()` raises `TypeError: 'Exists' object is not subscriptable`. `Q.deconstruct()` special-cases single-child Q objects as kwargs, assuming the child is a `(key, value)` tuple.

**Key code:** `django/db/models/query_utils.py`
- `Q` class starts at line 56.
- `Q.deconstruct()` starts at line 111.
- The faulty special case is line 116: `if len(self.children) == 1 and not isinstance(self.children[0], Q):`, followed by `kwargs = {child[0]: child[1]}`.
- `Q._combine()` lines 70–87 round-trips through `deconstruct()`, so malformed deconstruction also affects empty-Q combination paths.

**Tests:** `tests/queries/test_q.py`
- `QTests.test_deconstruct()` at lines 38–43 currently checks only kwargs-based deconstruction.
- Add coverage for `Q(x=1)` (single tuple child) and `Q(Exists(...))` / another non-subscriptable conditional child, asserting `args` rather than kwargs.

**Docs:** `docs/ref/models/querysets.txt` documents `Q` objects; the single-child deconstruction behavior is undocumented. `docs/topics/db/queries.txt` also covers Q usage but likely needs no change.

**Ruled out:** This is not a migration-writer or serializer bug; `Q.deconstruct()` itself produces invalid output. It is not specific to `Exists`; any non-subscriptable conditional child triggers it. Removing the special case entirely (PR 14126) changes `Q(x=1).deconstruct()` to args and is a broader backward-incompatible change.

**Conclusion:** Fix `Q.deconstruct()` by keeping the single-child special case but only using kwargs when the child is a length-2 tuple; otherwise deconstruct the child as an arg. This preserves existing `Q(x=1)` behavior while allowing `Q(Exists(...))`.
