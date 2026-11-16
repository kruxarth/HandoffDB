## Handoff: M2M serialization vs custom manager `select_related()`

**Issue:** Serializing an M2M field whose related model uses a custom default manager with `get_queryset().select_related("master")` raises `FieldError: Field TestTag.master cannot be both deferred and traversed using select_related at the same time`.

**Key files/lines:**
- `django/core/serializers/python.py:64-88` — `Serializer.handle_m2m_field()`; `queryset_iterator()` at `:81-82` calls `getattr(obj, field.name).only("pk").iterator()`.
- `django/core/serializers/xml_serializer.py:127-162` — same logic; `:157-158` calls `.only("pk").iterator()`.
- `django/core/serializers/base.py:143` invokes `handle_m2m_field()`; abstract definition at `:194`.
- `django/db/models/fields/related_descriptors.py:978+` — `create_forward_many_to_many_manager()`; related manager inherits the related model’s default manager behavior, including `select_related()`.
- `django/db/models/sql/query.py:798`, `:729` — `only("pk")` builds a select mask containing only `pk`.
- `django/db/models/sql/compiler.py:279`, `:1209-1211`; `django/db/models/query_utils.py:315-347` — compiler still sees the manager’s `select_related("master")` and raises because `master` is not in the `only()` mask.

**Tests/docs:** `tests/serializers/tests.py:260-290` covers serialization queries/prefetched M2M but not custom-manager `select_related()`. `tests/defer/tests.py:126`, `:316-328` documents the expected `only()` + `select_related()` conflict. Docs: `docs/ref/models/querysets.txt` around `select_related()`/`only()` (`:1104-1108`, `:1820`), and `docs/topics/serialization.txt`.

**Ruled out:** The `select_related_descend()` error is correct for user queries combining `only()` and `select_related()`. The serializer is not intentionally preserving related-manager traversal; it only needs PKs. Changing `only()` semantics or requiring a default manager is unnecessary.

**Conclusion:** In both M2M serializer paths, clear inherited `select_related()` before restricting fields, e.g. call `.select_related(None).only("pk").iterator()`. Add regression coverage using a custom manager with `select_related()` for both Python and XML serializers.
