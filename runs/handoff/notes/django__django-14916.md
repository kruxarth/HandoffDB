## Handoff: WhereNode clone performance feasibility

**Issue:** Investigate whether `WhereNode.clone()` can avoid looping over and cloning children, and whether `Node` can support shallow `__copy__`/`clone` semantics like `__deepcopy__`.

**Relevant code**
- `django/db/models/sql/where.py:142-160` — `WhereNode.clone()` currently creates a new instance and loops over `children`, calling `child.clone()` when available; `copy()` aliases `clone()`.
- `django/db/models/sql/where.py:198-202` — `resolve_expression()` clones, recursively resolves, then sets `clone.resolved = True`. `resolved` is class-level default at line 29.
- `django/db/models/sql/where.py` cached properties (`contains_aggregate`, `output_field`, around 210+) are the reason a full `clone.__dict__ = self.__dict__.copy()` is unsafe.
- `django/utils/tree.py:11-55` — `Node.__init__`, `_new_instance()` at 30, and `__deepcopy__()` at 50. `Node.add()` uses `_new_instance()` around line 92.
- `django/db/models/sql/query.py:306` — `Query.clone()` calls `self.where.clone()`.
- `django/db/models/query_utils.py:301` — `FilteredRelation.clone()`; Q combining copy handling around line 48.

**Tests**
- `tests/queries/tests.py:3044+` — `WhereNodeTest`.
- `tests/utils_tests/test_tree.py:7-93`, especially `test_deepcopy` at 73-77.
- `tests/queries/test_q.py:8+`, especially `test_combine_empty_copy` at 30-40.
- `tests/expressions/tests.py:1438` — `test_query_clone`.

**Ruled out:** Naively shallow-copying `WhereNode.__dict__` breaks because cached properties and post-`resolve_expression` state (`resolved`) must not be blindly aliased. Child cloning cannot simply be assumed unnecessary for every child type.

**Conclusion:** Feasible to optimize by creating `_new_instance(children=None, ...)` then assigning `clone.children = self.children[:]`, preserving cached/resolved behavior. A `Node.__copy__` mirroring `__deepcopy__` is plausible, with `clone`/`copy` as aliases. No related docs references found.
