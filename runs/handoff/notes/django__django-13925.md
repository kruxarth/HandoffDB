# Handoff: models.W042 false positive on inherited primary keys

## Issue
Django 3.2 alpha raised `models.W042` ("Auto-created primary key used when not defining a primary key type") on child models in multi-table inheritance whose PK is inherited from a parent that already declares an explicit primary key. Those models do **not** get an auto-created PK and must not warn.

## Key files/lines
- `django/db/models/base.py:1265-1290` — `Model.check()`; `_check_default_pk` is invoked via `_check_fields`.
- `django/db/models/base.py:1300-1320` — the W042 emission. The guard is essentially `cls._meta.pk.auto_created and not <setting overridden>`. This is the bug: for inherited models `_meta.pk` is the parent-link `OneToOneField`, which has `auto_created=True` but is not an `AutoField`.
- `django/db/models/options.py:252-290` — `Options._prepare()` promotes the parent link to PK (`field.primary_key = True; self.setup_pk(field)`) when `self.pk is None` and parents exist. This promotion is correct; do not change it.
- `django/db/models/base.py:195-290` — parent-link `OneToOneField` creation (`auto_created=True, parent_link=True`).
- `django/db/models/fields/related.py:461-470, 582-583, 1040-1060` — `parent_link` plumbing and `OneToOneField.deconstruct`.

## Tests
- `tests/check_framework/test_model_checks.py:365-430` — `ModelDefaultAutoFieldTests` (`mocked_is_overridden` at 365, `test_auto_created_pk` at 379). Add a case for multi-table inheritance with explicit parent PK here.
- `tests/check_framework/apps.py:4-10` — `CheckDefaultPKConfig`.
- `tests/model_inheritance/tests.py` — inheritance behaviour reference.

## Docs
`docs/ref/checks.txt` (W042), `docs/ref/settings.txt` (`DEFAULT_AUTO_FIELD`), `docs/releases/3.2.txt`.

## Ruled out
`Options._prepare()` PK promotion and parent-link construction are behaving correctly; the defect is isolated to the W042 guard. Could not run a live reproduction (`asgiref` missing in the environment).

## Conclusion
Tighten the W042 condition in `django/db/models/base.py:~1300` so it only fires when `cls._meta.pk` is an actual `AutoField` (e.g. add `isinstance(cls._meta.pk, AutoField)`), excluding parent-link `OneToOneField` PKs inherited from a concrete parent.
