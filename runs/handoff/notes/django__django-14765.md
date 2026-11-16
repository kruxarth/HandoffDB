## Handoff: ProjectState real_apps invariant

**Issue:** `ProjectState.__init__()` still defensively converts `real_apps` to a set, but PR #14760 made all internal callers pass a set. The constructor should assert the invariant when `real_apps` is non-`None` and assign directly.

**Key code:** `django/db/migrations/state.py:91-97` is the constructor. Current logic checks `isinstance(real_apps, set)` and converts otherwise. Change to assert `real_apps is None or isinstance(real_apps, set)`, then set `self.real_apps = real_apps or set()`. Other relevant references: `state.py:410-412` clones state with `real_apps=self.real_apps`; `graph.py:300-313` passes `real_apps` into `ProjectState`; `executor.py:69` passes `self.loader.unmigrated_apps`; `loader.py:338` passes `self.unmigrated_apps`, which is initialized and populated as a set at `loader.py:71,77,87,93,102`.

**Tests:** `tests/migrations/test_state.py:898-919` (`test_real_apps`) already constructs `ProjectState(real_apps={'contenttypes'})`. `tests/migrations/test_loader.py:98` checks `project_state.real_apps`; `tests/migrations/test_autodetector.py:2415,2434` assigns sets directly. No non-set `ProjectState(real_apps=...)` construction exists in `django/` or `tests/migrations/`.

**Docs:** No public docs document `ProjectState` as API; this is an internal-API invariant, so no docs update is needed.

**Ruled out:** External/non-set callers inside the repository; all discovered call sites pass sets or `None`. Defensive conversion is therefore unnecessary.

**Conclusion:** Simplify `state.py:91-97` to assert the set invariant and remove conversion. Existing tests cover normal set usage; optionally add a small assertion test for a non-set `real_apps`.
