## Handoff: system checks for invalid functional index fields

**Issue:** `Meta.indexes` functional indexes (e.g. `Index(Lower("missing_field"), name="...")`) are not validated by system checks. Follow-up to #26167.

**Relevant code:**
- `django/db/models/base.py:1624-1704` — `Model._check_indexes()` validates index names, conditions, `fields`, and `include`, but only passes `index.fields`/`include` to `_check_local_fields()`; functional `index.expressions` are not checked.
- `django/db/models/base.py:1706-1754` — `_check_local_fields()` emits `models.E012`/`E013` for missing or M2M fields.
- `django/db/models/base.py:1933-1946` — `_get_expr_references()` recursively extracts `F`/`Q` references from expressions; useful model for collecting functional-index field names without resolving against a `Query`.
- `django/db/models/indexes.py:78-99` — `Index.contains_expressions` and expression resolution. Resolution can raise `FieldError` for missing fields.
- `django/core/checks/model_checks.py` — `check_all_models()` only collects index names for duplicate-name checks, not expression fields.

**Tests:** `tests/invalid_models_tests/test_models.py`, `IndexesTests` around lines 237-456, especially missing-field (`~239-250`), M2M (`~252-266`), non-local field (`~268-300`), and include missing field (`~423-437`). `tests/model_indexes/tests.py` covers functional index behavior.

**Docs:** likely `docs/ref/checks.txt` (`models.E012`/`E013`) and `docs/ref/models/indexes.txt`.

**Ruled out:** using `Query._gen_cols()`; resolving expressions with non-existent fields raises `FieldError`. Existing checks only cover `fields`/`include`, not `expressions`.

**Conclusion:** extend `_check_indexes()` to inspect functional index expressions, collect referenced field paths via an `_get_expr_references`-style walk, and validate them with local-field checks.
