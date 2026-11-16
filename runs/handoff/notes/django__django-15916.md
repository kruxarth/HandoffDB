## Handoff note: ModelForm Meta `formfield_callback`

**Issue:** `modelform_factory()` ignores `formfield_callback` declared in a supplied base form’s `Meta`. Example: `MyForm.Meta.formfield_callback = all_required`, but `modelform_factory(MyModel, form=MyForm)` produces fields that are not required because the factory overrides the inherited callback with `None`.

**Relevant code:** `django/forms/models.py`
- `modelform_factory()`: lines 563–639. The default argument is `formfield_callback=None` at line 568. Lines 633–634 only set `Meta.formfield_callback` when truthy. Critically, line 639 always puts `"formfield_callback": formfield_callback` into `form_class_attrs`, so a `None` is passed explicitly.
- `ModelFormMetaclass`: lines 258–266. It already derives `base_formfield_callback` from base classes’ `Meta` (lines 260–263), then uses `attrs.pop("formfield_callback", base_formfield_callback)` at line 266. The factory’s explicit `None` defeats this fallback.
- `fields_for_model()`: lines 135–228, especially callback handling at 223–228. This is downstream; the callback is not reaching it.

**Tests:** `tests/model_forms/tests.py:3445–3488` covers explicit `modelform_factory(..., formfield_callback=...)`, including invalid callback types. `tests/model_formsets_regress/tests.py:388–402` covers explicit callbacks for inline/model formsets. No test covers a callback inherited from `form.Meta`.

**Docs:** `docs/ref/forms/models.txt:14–27` documents `modelform_factory` and its `formfield_callback` argument. `docs/topics/forms/modelforms.txt:528–599` discusses `Meta` field customization.

**Ruled out:** Explicit `formfield_callback=` works. Formset factories and admin pass callbacks explicitly. `ModelFormMetaclass` inheritance logic works; the bug is the factory passing `None` at line 639.

**Conclusion:** Fix `modelform_factory()` so an omitted callback does not override the base form’s `Meta.formfield_callback`—e.g. only include `"formfield_callback"` in `form_class_attrs` when provided, or fall back to the base form’s `Meta`/attribute. Add regression coverage for `modelform_factory(Model, form=BaseFormWithMetaCallback)`.
