## Handoff note

**Issue:** `call_command()` mishandles required mutually exclusive arguments that share the same `dest` (e.g. `--for`/`--until` both targeting `until`). CLI parsing works, but programmatic calls reconstruct both flags, so the wrong action is always required and the value is parsed by the wrong type.

**Key code:** `django/core/management/__init__.py:115-122` builds the parser and `opt_mapping`; lines 118-121 collapse option strings to `dest`, losing which specific option was supplied. `django/core/management/__init__.py:130-150` collects parser actions and `mutually_exclusive_required_options`, then rebuilds required options by checking only `opt.dest in options`. With a shared `dest`, every action in the required group matches, so both `--for=...` and `--until=...` are appended to `parse_args`. `django/core/management/base.py:314-318` (`create_parser`) and `:321-336` (`add_arguments`) confirm the CLI path is not the problem.

**Tests:** Existing coverage is in `tests/user_commands/tests.py:106-122` (`call_command` option parsing) and the mutually exclusive test around `:220-250`. `tests/user_commands/management/commands/mutually_exclusive_required.py` only uses distinct dests, so it misses this case; add a command with two required group options sharing `dest`, plus regression tests. `required_option.py` and `subparser_dest.py` were checked and ruled out.

**Docs:** `docs/ref/django-admin.txt` (`call_command`) and `docs/howto/custom-management-commands.txt` (mutually exclusive groups) are the relevant references; likely no doc change unless behavior is clarified.

**Conclusion:** Root cause is `call_command()`’s dest-based required-option reconstruction. It must retain the supplied option/action identity and only re-add the matching action, not all actions sharing that `dest`.
