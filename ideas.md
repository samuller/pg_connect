# Ideas

An idea/planning list:

- Lots of possible ways in which requirements might vary.
- Helps to keep in mind to prevent designs that preclude these as future avenues.

## Import

- Insertion order based on dependencies:
  - Table order.
  - Order of rows within tables (when tables self-reference).
- Speed vs. impact options:
  - Bulk import: faster, but might lock tables which affects active system which is in use.
  - Incremental import: slower, but [maximizes table availability][1] since locks are for short time.

[1]:[https://blog.codacy.com/how-to-update-large-tables-in-postgresql-e9aecd197fb7?gi=dc843a01e10b]

## Merge

Identity columns:

- All columns with unique attributes, i.e. primary keys plus columns with unique constraints.
- Only some columns that are unique.
- [Partial unique indexes][1]
- Any columns asserted as unique (even if not enforced on database level), but with checks that alert if assumption broken.

[1]:[https://www.postgresql.org/docs/current/static/indexes-partial.html]

## File format

- Support forwarding options to COPY to allow supporting all its formats.
- Column typing: files are always text format and each cell should be convertible from text to it's column type
- Rows:
  - Exact: files describe exactly how final table should be. You can practically drop table and import file into new equivalent.
  - New/Update: files describe new or update rows that need to exist in table.
  - Removals: files that contain specific rows to remove.
- Columns:
  - Exact: files have data for each column in table.
  - Partial: files are missing some columns which should then be left untouched (not cleared).
  - Additional: files have extra columns that need to be ignored.
  - Modified: files have columns that need to be transformed/processed/merge/split to get final column data.
  - Mixed: files have columns that could be from completely different tables.

## Folder structure

- File vs. table:
  - Exact: each file contains only data for one distinct table.
  - Multiple: more than one file possible per table.
  - Merged: multiple table's data in one file.
- Names:
  - Exact: each file has name of table and contains all data destined for that table.
  - Conceptual: each filename describes application/business logic concept and configuration specifies final table/s.