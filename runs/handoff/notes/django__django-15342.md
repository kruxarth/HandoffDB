## Handoff: `_order` field crash in migration autodetector

**Issue:** `makemigrations`/`migrate` crashes with `KeyError: 'order_with_respect_to'` for models that have a field named `_order` but do not set `Meta.order_with_respect_to`, e.g. django-simple-history historical models.

**Root cause:** `ModelState.get_field()` in `django/db/migrations/state.py:687-691` unconditionally remaps `_order` to `self.options['order_with_respect_to']`. The traceback points at line 689. This was introduced by commit `aa4acc164d1247c0de515c959f7b09648b57dc42`.

**Call path:** `django/db/migrations/autodetector.py:944-948` (`generate_altered_fields`) calls `get_field()` for old/new fields. Field-key generation is at `autodetector.py:213-222`; it correctly includes literal `_order`, so the failure is only in `get_field()`.

**Fix:** Guard the remap:
```python
if field_name == '_order' and 'order_with_respect_to' in self.options:
    field_name = self.options['order_with_respect_to']
```

**Tests:** Add regression coverage in `tests/migrations/test_state.py`, near the existing `order_with_respect_to` tests: `test_order_with_respect_to_private_field` around `tests/migrations/test_state.py:1594-1607`, and `test_ignore_order_wrt` at `tests/migrations/test_state.py:931`. A `ModelState` with a literal `_order` field and no option should return that field, not raise.

**Ruled out:** Autodetector field-key construction and migration operations handling `order_with_respect_to` in `django/db/migrations/operations/models.py:566-577` are not the source. The private-field case is already handled by excluding the option from `ModelState.options`.

**Docs:** Relate to `docs/ref/models/options.txt` (`order_with_respect_to`) and migration docs; no docs change likely needed for this defensive fix.

**Conclusion:** Confirmed bug in `ModelState.get_field()`; guard the option lookup and add a regression test.
