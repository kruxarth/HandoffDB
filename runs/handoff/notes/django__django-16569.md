## Handoff: FormSet `add_fields()` crashes when `index is None`

**Issue:** With `can_delete=True` and `can_delete_extra=False`, calling `empty_form()` raises `TypeError: '<' not supported between instances of 'NoneType' and 'int'`.

**Root cause / files:**
- `django/forms/formsets.py`, `BaseFormSet.add_fields()` lines 475–497. The deletion-field condition at **line 493** is `if self.can_delete and (self.can_delete_extra or index < initial_form_count):`; it compares `None` to an int.
- `empty_form` calls `add_fields(form, None)` at **line 267**; normal form construction calls it with an integer at **line 243**.
- The ordering branch at **line 480** already guards with `index is not None`, showing the intended pattern.
- Factory defaults for `can_delete_extra` are at **lines 541 and 561**.

**Related code:** `django/forms/models.py` `BaseModelFormSet.add_fields()` lines 949–997 and `BaseInlineFormSet.add_fields()` lines 1144–1145 delegate to the base implementation but do not cause this path.

**Tests/docs:** Relevant tests live in `tests/forms_tests/tests/test_formsets.py` (add a regression test for `empty_form()` with `can_delete=True`, `can_delete_extra=False`). Docs: `docs/ref/forms/formsets.txt` and `docs/topics/forms/formsets.txt`.

**Ruled out:** The ordering-field branch (already None-safe); model/inline formset overrides (they delegate); `can_delete_extra=True` (short-circuits before comparison).

**Conclusion/fix:** Change line 493 to:
```python
if self.can_delete and (self.can_delete_extra or (index is not None and index < initial_form_count)):
```
No test run was performed in this session.
