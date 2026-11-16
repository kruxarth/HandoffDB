# Handoff: `Field.__hash__` immutability

**Issue:** `Field.__hash__` changes after a field is assigned to a model, breaking fields used as dict keys before model-class creation. Regression from #31750.

**Key code — `django/db/models/fields/__init__.py`:**
- `Field.__init__` lines 164–168: sets stable `creation_counter`.
- `Field.__eq__` lines 516–523: compares `creation_counter` and `model`; this fix should remain.
- `Field.__lt__` lines 526–537: ordering uses `creation_counter`; unaffected.
- `Field.__hash__` lines 544–546: currently includes `self.model`, which is populated later during `contribute_to_class`, so the hash changes. Revert to hashing only `self.creation_counter`; hash collisions are valid because `__eq__` still checks `model`.

**Tests:** `tests/model_fields/tests.py`
- `BasicFieldTests.test_abstract_inherited_fields` (starts ~line 105); lines 131–133 assert distinct hashes for abstract/inherited fields. These assertions will fail after the revert and should be removed/changed—unequal fields may share a hash.
- Add a regression test matching the issue: put a standalone `models.CharField` in a dict, assign it to a model class, and assert it remains present.
- `tests/model_fields/test_imagefield.py` hash tests and `tests/m2m_through/tests.py:28` are unrelated. Other `__hash__` implementations (`lookups.py`, `expressions.py`, etc.) are unrelated.

**Docs:** No documentation describes `Field.__hash__`; no doc update needed.

**Ruled out:** Equality/ordering semantics, image-field hashing, m2m-through hashing.

**Conclusion:** Confirmed bug is the `model` component in `Field.__hash__`; revert that component while keeping the `__eq__` fix.
