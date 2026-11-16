## Handoff note

**Issue:** A concrete child field named the same as an inherited `@property` from an abstract base leaves the property in place; `Model.__init__` then calls `setattr()` on it and raises `AttributeError: can't set attribute`.

**Key files/lines**
- `django/db/models/fields/__init__.py:774-800` — `Field.contribute_to_class()`. Root cause is the guard around line 789: `if not getattr(cls, self.attname, None): setattr(cls, self.attname, self.descriptor_class(self))`. An inherited property is truthy, so the child field descriptor is not installed.
- `django/db/models/base.py:180-330` — `ModelBase.__new__` abstract-base field collection/inheritance; confirms how inherited attributes and locally declared fields are processed.
- `django/db/models/base.py:1440-1490` — `_check_field_name_clashes()` only compares fields between parents/children, not inherited Python properties.
- `django/db/models/base.py:1531-1560` — existing property/related-accessor clash check (`models.E025`), which is narrower than this case.
- `django/db/models/query_utils.py:94` — `DeferredAttribute` descriptor installed by fields.

**Tests/docs**
- `tests/model_inheritance/test_abstract_inheritance.py:134` — `test_override_field_with_attr`; related inheritance tests at lines 37-188.
- `tests/invalid_models_tests/test_models.py:808-895` — `ShadowingFieldsTests`; property/accessor clash test at line 1211.
- `docs/ref/checks.txt:364-366` — documents `models.E025`.

**Ruled out**
- Existing field-clash checks do not catch inherited properties.
- The `models.E025` check only covers related-field accessors.
- No existing regression test covers this scenario.
- Reproduction could not be executed because `asgiref` is missing from the environment.

**Conclusion**
The likely fix is in `Field.contribute_to_class()`: allow a concrete child field descriptor to override an inherited property, consistent with documented support for overriding normal Python attributes. Add a regression test in `tests/model_inheritance/test_abstract_inheritance.py`; a system check is an alternative but would contradict the documented override behavior.
