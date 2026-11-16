## Handoff: autocomplete broken for inherited models

**Issue:** After #29138, `AutocompleteMixin.optgroups()` computes `to_field_name` as `foo_ptr` instead of `id` for a child model (`Bar(Foo)`) with an inherited `ManyToManyField`. The subsequent filter at `django/contrib/admin/widgets.py:434` then queries `Tag` with `foo_ptr__in`, raising `FieldError`.

**Key code:**
- `django/contrib/admin/widgets.py:376` (`AutocompleteMixin`), `:420-434` (`optgroups`). The bug is line 431: `getattr(self.field.remote_field, 'field_name', self.field.model._meta.pk.name)`. For inherited models the fallback uses the *child's* PK (`foo_ptr`), not the related model's PK.
- `django/contrib/admin/options.py:220-242` / `:244-284`: widget construction; confirmed `AutocompleteSelect` receives the correct field, so this layer is not at fault.
- `django/db/models/options.py:271-303`: parent-link PK promotion explains why `_meta.pk.name` is `foo_ptr`.
- `django/db/models/fields/reverse_related.py:170-178`, `:254-255`: `field_name` defaulting; the remote model's PK is the correct source.
- `django/contrib/admin/views/autocomplete.py:93`: same incorrect pattern (`model_admin.model._meta.pk.name`); likely needs the same fix.

**Tests:** `tests/admin_widgets/test_autocomplete_widget.py` (`AutocompleteMixinTests`) is the right home; add an inherited-model case using `tests/admin_widgets/models.py` and `widgetadmin.py`.

**Docs:** `docs/ref/contrib/admin/` (`autocomplete_fields`) describes behavior; no doc change expected for a pure bug fix.

**Ruled out:** `options.py` formfield wiring, `get_field_queryset()`, and the `Tag` model itself. Not reproducible in this environment (`asgiref` missing, Python 3.14), so no test run.

**Conclusion:** Change the fallback to the remote related model's PK `attname` in both `widgets.py:431` and `views/autocomplete.py:93`, then add the regression test.
