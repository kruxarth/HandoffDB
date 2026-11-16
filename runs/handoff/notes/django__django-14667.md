# Handoff: `defer()` after `only()` drops field restriction

Issue: `Company.objects.only("name").defer("name")` selects all columns; expected only `id`. Chaining another `.defer("country")` still selects all columns.

Mattered code:
- `django/db/models/query.py:1210-1244` — `defer()` / `only()` clone and call `Query.add_deferred_loading()` / `add_immediate_loading()`.
- `django/db/models/sql/query.py:227` — `deferred_loading` is `(frozenset, defer_flag)`; `True` means exclude listed fields, `False` means include only listed fields.
- `django/db/models/sql/query.py:2067-2113` — state transitions. `only("name")` becomes `({"name"}, False)`; `.defer("name")` becomes `(set(), False)`. An empty “only” set is indistinguishable from “no restriction.”
- `django/db/models/sql/query.py:668-745` — `deferred_to_data()` returns early at line 680 when `field_names` is empty, so the compiler treats the query as unrestricted.
- `django/db/models/sql/compiler.py:700-721`, `1118-1125` — projection consumes `deferred_to_columns()`, downstream of the bad state.

Tests: `tests/defer/tests.py:48-53` covers chaining but not this exact only-then-defer-same-field case; add regression there. `tests/defer/models.py` provides `Primary`/`Secondary`. Docs: `docs/ref/models/querysets.txt` sections for `defer()` and `only()`.

Ruled out: compiler column filtering works; `only("name","country").defer("name")` correctly yields `id,country`. `defer(None)` uses `clear_deferred_loading()` and is separately tested at `tests/defer/tests.py:60-64`.

Conclusion: bug is in deferred-loading state representation/transition. Empty immediate (`only`) state must not be treated as unrestricted; likely adjust `deferred_to_data()` early return and/or normalize `add_deferred_loading()` to preserve “only pk” semantics. No patch applied.
