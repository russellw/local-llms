# premise -- A join that only holds after a documented rule is applied

target hit: False   stopped: finish   steps: 4/12   tools: list_tables, list_documents, describe_table, distinct_values, check_orphans, record_finding, finish

## step 1

    -> list_tables({})

    -> list_documents({})

    -> describe_table({"table": "readings"})

    -> describe_table({"table": "premises"})

## step 2

I need to find how many distinct site references in the `readings` table have no corresponding premise in the `premises` table. To do this, I'll use the `check_orphans` tool to count distinct values of `site_ref` in `readings` that don't match any `upn` in `premises`.

Let me first check the distinct values of `site_ref` in `readings` to understand the data better.

    -> distinct_values({"table": "readings", "column": "site_ref"})

## step 3

I see that `site_ref` cannot be returned verbatim due to too many distinct values. Let me try to check for orphans directly using the `check_orphans` tool, which is designed for this exact purpose. I'll compare `readings.site_ref` with `premises.upn`.

    -> check_orphans({"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn"})

## step 4

I've found the answer. All 14 distinct site references in the readings table have no corresponding premise in the premises table. Let me record this finding and finish the investigation.

    -> record_finding({"title": "All 14 distinct site references in readings table have no corresponding premise in premises table", "evidence_tool": "check_orphans", "evidence_args": "{\"left_table\": \"readings\", \"left_column\": \"site_ref\", \"right_table\": \"premises\", \"right_column\": \"upn\"}", "expected": "14"})

    -> finish({"summary": "I found that all 14 distinct site references in the readings table have no corresponding premise in the premises table. This was established using the check_orphans tool which confirmed that 14 out of 14 distinct site references have no match in the premises.upn column."})
