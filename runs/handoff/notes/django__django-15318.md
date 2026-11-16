## Handoff note: unify unsaved reverse FK and M2M querying

**Issue:** Reverse FK access on an unsaved instance returns an empty queryset, while M2M access raises `ValueError`. Goal is consistent behavior per #17541: unsaved relation access raises; nullable FK/M2M relation access returns an empty queryset; adding through a null FK relation raises.

**Key code:** `django/db/models/fields/related_descriptors.py`
- `ReverseManyToOneDescriptor` (`544-610`) and `create_reverse_many_to_one_manager()` (`612-852`): reverse FK manager. `get_queryset()` at `685` currently permits unsaved instances to produce an empty queryset; `add/create/remove/clear/set` at `716-852` need matching null/unsaved checks.
- `ManyToManyDescriptor` (`854-910`) and `create_forward_many_to_many_manager()` (`912+`): M2M manager. Validation at `957-967` raises for null relation fields and missing PKs; `get_queryset()` at `1014` is the counterpart to adjust for nullable M2M fields.
- Descriptor wiring only: `django/db/models/fields/related.py:525,1917,1932`; not behavior.
- `django/contrib/contenttypes/fields.py:535` subclasses reverse FK descriptor; check compatibility but not primary.

**Tests/docs:**
- `tests/many_to_one/tests.py:740-752` (`test_relation_unsaved`) asserts current reverse FK empty-queryset behavior.
- `tests/m2m_through_regress/tests.py:160-210` covers null `to_field` and unsaved PK M2M errors.
- `tests/many_to_many/tests.py:30-40` covers unsaved M2M add error.
- Related docs: `docs/releases/1.8.txt:693`, `docs/releases/1.8.5.txt:44`; add release note under `docs/releases/4.1.txt` Models section (`250`).

**Ruled out:** Descriptor assignment code in `related.py`; generic-relation subclass as root cause.

**Conclusion:** Implement checks in reverse FK and M2M manager paths so unsaved access raises consistently, nullable relations return empty querysets, and null FK additions raise. No edits or tests were run.
