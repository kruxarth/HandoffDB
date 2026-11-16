## Handoff note

**Issue:** `DEFAULT_AUTO_FIELD` pointing at a subclass of `BigAutoField`/`SmallAutoField` (e.g. `MyBigAutoField(models.BigAutoField)`) crashes during model import with `ValueError: ... must subclass AutoField`.

**Key code:** `django/db/models/fields/__init__.py:2502-2527` defines `AutoFieldMeta`. Its `_subclasses` property (`:2519-2521`) returns only `(BigAutoField, SmallAutoField)`, and `__subclasscheck__` (`:2526-2527`) uses exact tuple membership: `subclass in self._subclasses`. A subclass of `BigAutoField` is not in that tuple, and the fallback `super().__subclasscheck__()` fails because `BigAutoField`/`SmallAutoField` are not true `AutoField` subclasses. `__instancecheck__` (`:2523-2524`) already uses `isinstance(instance, self._subclasses)`, so it correctly handles subclasses.

`django/db/models/options.py:221-246` is the consumer: `_get_default_pk_class()` imports the configured class and checks `issubclass(pk_class, AutoField)` at `:245-246`. Import/settings resolution and app-config override logic were ruled out; they work correctly.

**Tests:** `tests/model_fields/test_autofield.py:25-34` (`AutoFieldInheritanceTests`) covers `issubclass(BigAutoField/SmallAutoField, AutoField)` but not their subclasses. Add regression cases there. `tests/model_options/test_default_pk.py:1-46` covers invalid `DEFAULT_AUTO_FIELD` values; add a case using a custom `BigAutoField` subclass.

**Docs:** `docs/ref/settings.txt` (`DEFAULT_AUTO_FIELD`) and `docs/ref/models/fields.txt` (`AutoField`, `BigAutoField`, `SmallAutoField`).

**Conclusion:** Fix `AutoFieldMeta.__subclasscheck__` to allow subclasses of `_subclasses`, e.g. `return issubclass(subclass, self._subclasses) or super().__subclasscheck__(subclass)`. Add regression tests for custom subclasses of `BigAutoField` and `SmallAutoField`.
