## Issue
Assigning an unsaved model to a `GenericForeignKey` (GFK) is not rejected on `save()`, unlike `ForeignKey`/`OneToOneField` (ticket #10811 behavior). If `gfk_id` is nullable this silently loses data. After saving the related object, accessing `gfk` queries `pk=None`, returns `None`, and effectively unassigns it while leaving `gfk_ctype` set.

## Code
- `django/db/models/base.py:1073` `_prepare_related_fields_for_save()` iterates only `self._meta.concrete_fields`. GFK is a private, non-concrete field, so it is never validated. Called from `base.py:786` (`save()`), `django/db/models/query.py:568` (`bulk_create`) and `:742` (`bulk_update`), so fixing the helper covers all paths.
- `django/contrib/contenttypes/fields.py:22` `GenericForeignKey`; `__get__` at `:233-250`: `pk_val = getattr(instance, self.fk_field)` (`:233`), cache check (`:235-236`), `pk_match` (`:242`), redundant `ct.get_object_for_this_type(pk=pk_val)` (`:250`). When `pk_val is None`, use the cached object's PK to update `fk_field` and return it, skipping the query.

## Tests/docs
- `tests/generic_relations/tests.py:504` `test_unsaved_instance_on_generic_foreign_key` currently asserts `IntegrityError`; should become `ValueError` matching the FK message.
- `tests/generic_relations/tests.py:286` `test_add_rejects_unsaved_objects`; `:537` `test_assign_content_object_in_init`.
- Models: `tests/generic_relations/models.py:17` `TaggedItem`, `:121` `ManualPK`, `:149` `AllowsNullGFK`.
- `tests/contenttypes_tests/test_fields.py` `GenericForeignKeyTests`, esp. cache behavior around `:33`.
- Docs: `docs/ref/contrib/contenttypes.txt:266-360`; `docs/releases/4.1.txt`.

## Ruled out
`GenericRelation` (`fields.py:291`) is the reverse side and unrelated. ContentType resolution and `get_prefetch_queryset` are fine. The concrete-only iteration is the root cause.

## Conclusion
Extend `_prepare_related_fields_for_save()` to include private GFK fields, raising `ValueError("save() prohibited to prevent data loss due to unsaved related object '<name>'.")`; patch `GenericForeignKey.__get__` for `pk_val=None`.
