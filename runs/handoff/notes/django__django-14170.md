# Handoff: `__iso_year` lookup broken by YearLookup BETWEEN optimization

## Issue
`YearLookup` rewrites year comparisons into `BETWEEN <year-01-01> AND <year-12-31>` to use indexes. This optimization is wrongly applied to the `iso_year` lookup. ISO years do not align with calendar years (e.g. 2016-01-01 belongs to ISO year 2015), so `filter(start_date__iso_year=2020)` returns incorrect rows. `ExtractIsoYear` used alone in an annotation is correct; only the lookup/filter path is affected. The explicit-annotation filter (`filter(extracted=2020)`) also degrades to `BETWEEN`.

## Files that matter
- `django/db/models/lookups.py:540-571` — `YearLookup`; `as_sql` (549-561) performs the `BETWEEN` rewrite when `rhs_is_direct_value()`.
- `django/db/models/lookups.py:572-595` — `YearExact`, `YearGt`, `YearGte`, `YearLt`, `YearLte` subclasses.
- `django/db/models/functions/datetime.py:93-95` — `ExtractIsoYear` (`lookup_name = 'iso_year'`).
- `django/db/models/functions/datetime.py:150` — `DateField.register_lookup(ExtractIsoYear)`.
- `django/db/models/functions/datetime.py:167-171` — **the defect**: registers `YearExact/YearGt/YearGte/YearLt/YearLte` on `ExtractIsoYear`, pulling in the calendar-year `BETWEEN` optimization.

## Tests / docs
- `tests/db_functions/datetime/test_extract_trunc.py:93` (`test_extract_year_exact_lookup`, loops `year`/`iso_year`), `:329` (`test_extract_iso_year_func`), `:348`, `:350` (`test_extract_iso_year_func_boundaries`).
- Revert the invalid test edits; extend the boundary test to assert correct ISO-year filtering (e.g. dates near Jan 1 / Dec 31).

## Ruled out
`ExtractIsoYear` alone in annotations works; `resolve_expression`/DurationField validation (datetime.py:65-82) is unrelated; the lookup registration in `RegisterLookupMixin` behaves correctly.

## Conclusion
Remove the `Year*` registrations at `datetime.py:167-171` so `iso_year` falls back to plain `EXTRACT`-based exact/gt/gte/lt/lte, keeping the `BETWEEN` optimization for calendar `year` only.
