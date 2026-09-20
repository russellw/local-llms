# premise -- A join that only holds after a documented rule is applied

target hit: False   stopped: finish   steps: 5/12   tools: list_tables, list_documents, describe_table, sample_column, check_orphans, record_finding, finish

## step 1

    -> list_tables({})

    -> list_documents({})

    -> describe_table({"table": "readings"})

    -> describe_table({"table": "premises"})

## step 2

I need to find how many distinct site references in the `readings` table have no corresponding premise in the `premises` table. To do this, I'll use the `check_orphans` tool to count distinct values of `site_ref` in `readings` that don't match any `upn` in `premises`.

Let me first check the structure of the data to make sure I understand the relationship between the tables.

    -> sample_column({"table": "readings", "column": "site_ref", "n": "5"})

## step 3

I see that `site_ref` values follow the shape "AAAA-9999" (uppercase letters and digits). Now I'll check the `premises` table's `upn` column to understand its format.

    -> sample_column({"table": "premises", "column": "upn", "n": "5"})

## step 4

Now I'll check for orphans - specifically, I'll count how many distinct `site_ref` values in the `readings` table do not have a matching `upn` in the `premises` table.

    -> check_orphans({"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn"})

## step 5

I've found that all 14 distinct site references in the readings table have no corresponding premise in the premises table. This means there are 14 orphaned site references.

Let me record this finding:

    -> record_finding({"title": "All 14 distinct site references in readings table have no corresponding premise in premises table.", "evidence_tool": "check_orphans", "evidence_args": "{\"left_table\": \"readings\", \"left_column\": \"site_ref\", \"right_table\": \"premises\", \"right_column\": \"upn\"}", "expected": "14"})

    -> finish({"summary": "I found that all 14 distinct site references in the readings table have no corresponding premise in the premises table, indicating 14 orphaned site references."})
