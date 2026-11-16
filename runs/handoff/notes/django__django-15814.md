## Handoff: proxy model `select_related()` + `only()` crash

**Issue:** `AnotherModel.objects.select_related("custom").only("custom__name")`, where `custom` is an FK to a proxy model, raises `ValueError: 'id' is not in list` in `RelatedPopulator.__init__` when resolving `pk_idx`.

**Key code:**
- `django/db/models/sql/query.py:721-805` — `Query.deferred_to_data()`. This is the root cause. It builds the deferred-field map consumed by the compiler, but proxy-model metadata is not consistently normalized to the concrete model. The `opts` assignment around line 745 and the `cur_model`/`model` traversal around lines 740-776 matter: proxy vs. concrete model keys cause the related model’s PK column to be absent from the deferred init list.
- `django/db/models/sql/compiler.py:1313` — calls `query.deferred_to_data(columns)`.
- `django/db/models/sql/compiler.py:245-286`, `799-832`, `1000-1200` — `klass_info`, `select_fields`, and `get_related_selections()`/`get_default_columns()`; these compare concrete models, so `deferred_to_data()` must agree.
- `django/db/models/query.py:2534-2620` — `RelatedPopulator`; failure at line 2599 (`self.init_list.index(self.model_cls._meta.pk.attname)`), invoked via `get_related_populators()` line 2620.

**Tests:**
- `tests/defer/tests.py:244-260` — existing `test_defer_proxy`, but it does not cover FK-to-proxy + `only("custom__name")`.
- `tests/defer_regress/tests.py:150-170`, `224` — proxy `only()`/`defer()` and proxy `select_related()` coverage.
- `tests/defer/models.py:32,37` — proxy model fixtures.

**Ruled out:** `RelatedPopulator` itself and plain `select_related()` are not independently broken; the crash is caused by inconsistent deferred-column metadata for proxy models. No docs changes identified.

**Conclusion:** Normalize proxy metadata to `concrete_model._meta` while collecting deferred fields in `deferred_to_data()`, and add a regression test using an FK to a proxy with `select_related(...).only("custom__name")`.
