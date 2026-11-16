# Handoff: Support `reversed()` on `OrderedSet`

**Issue:** `OrderedSet` is ordered but not reversible; `reversed(OrderedSet(...))` fails because no `__reversed__()` exists. Fix is to add one.

**Key code:** `django/utils/datastructures.py`, lines 5–35. `OrderedSet` stores insertion order in `self.dict` (`dict.fromkeys`, line 11). `__iter__` (lines 25–26) returns `iter(self.dict)`, so iteration already follows insertion order. Insert `__reversed__` next to `__iter__`, returning `reversed(self.dict)`. That delegates to dict's reverse-key iteration and avoids a materialized list copy, consistent with the existing design.

**Tests:** `tests/utils_tests/test_datastructures.py`, `OrderedSetTests` (starts line 15). Existing methods cover `__init__`, `remove`, `discard`, `__contains__`, `__bool__`, `__len__` (lines 17–57); none cover reversal. Add a `test_reversed` there, e.g. build `OrderedSet([1, 2, 3])`, assert `list(reversed(s)) == [3, 2, 1]`, and consider empty-set and single-element cases. Note `OrderedSet` has no `__getitem__`, so `reversed()` must go through `__reversed__`, not the sequence protocol.

**Docs:** No dedicated `OrderedSet` docs page exists; `django/utils/datastructures.py` is internal API, so no `docs/` change is expected. Verify with a quick grep before closing.

**Ruled out:** No separate `OrderedSet` module or test file exists (the `find` for `*ordered_set*`/`*orderedset*` returned nothing); all usage is in `datastructures.py` and the single test module above. No changes to `MultiValueDict` or other classes in the file.

**Conclusion:** One-method addition (`__reversed__` in `OrderedSet`, ~line 27) plus one test. Low risk; behavior mirrors dict key order.
