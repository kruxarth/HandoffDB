## Handoff note

**Issue:** Admin inline saving nulls a non-PK `UUIDField` alternate key (`Thing.id`) when a new parent and child are submitted. The parent is new, so `BaseInlineFormSet.add_fields()` treats the inline FK’s `to_field` as a defaulted PK and sets it to `None`, corrupting the parent’s unique UUID.

**Key files/lines:**
- `django/forms/models.py:1152-1183` — `BaseInlineFormSet.add_fields()`. Lines `1167-1181` are the bug: for `self.instance._state.adding`, it resolves `to_field` (or PK) and nulls it whenever `to_field.has_default()`. It should only reset the parent’s auto-generated primary key, not an alternate key used by the inline FK.
- `django/forms/models.py:1338-1370` — `InlineForeignKeyField`; relevant because it reads/compares the parent’s `to_field` value.
- `django/forms/models.py:1080-1105` — formset initializes parent instance/queryset; confirms new-parent path.
- `django/contrib/admin/options.py:1781-1900`, `2270-2295` — admin add/change and formset kwargs; ruled out as the source.

**Tests/docs:** Existing coverage is `tests/model_formsets/test_uuid.py:83-95` (`test_inlineformset_factory_nulls_default_pks_alternate_key_relation`) using `ParentWithUUIDAlternateKey`/`ChildRelatedViaAK` in `tests/model_formsets/models.py:256-264`. Related docs: `docs/topics/forms/modelforms.txt` (inline formsets) and `docs/ref/contrib/admin/index.txt` (inlines).

**Ruled out:** Model `save()`/`_do_insert`, `Field.pre_save()`, SQL compiler value preparation, and admin view/formset construction. The nulling is applied earlier in `BaseInlineFormSet.add_fields()`.

**Conclusion:** Fix `BaseInlineFormSet.add_fields()` so only the parent PK is nulled for unsaved parents; do not null alternate `to_field` values merely because they have defaults. Add/adjust regression coverage for alternate-key inline relations.
