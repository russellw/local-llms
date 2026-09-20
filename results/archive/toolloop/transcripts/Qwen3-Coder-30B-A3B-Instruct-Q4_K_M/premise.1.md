# premise -- A join that only holds after a documented rule is applied

target hit: False   stopped: finish   steps: 3/12   tools: list_tables, list_documents, describe_table, check_orphans, record_finding, finish

## step 1

    -> list_tables({})

    -> list_documents({})

    -> describe_table({"table": "readings"})

    -> describe_table({"table": "premises"})

## step 2

I need to find how many distinct site references in the `readings` table have no matching premise in the `premises` table. The `site_ref` column in `readings` should correspond to the `upn` column in `premises`. I'll use the `check_orphans` tool to count these unmatched references.

    -> check_orphans({"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn"})

## step 3

I found that all 14 distinct site references in the readings table have no matching premise in the premises table. This means there are 14 orphaned site references that do not correspond to any premise.

Let me record this finding and finish the investigation.

    -> record_finding({"title": "All 14 distinct site references in readings table have no matching premise in premises table.", "evidence_tool": "check_orphans", "evidence_args": "{\"left_table\": \"readings\", \"left_column\": \"site_ref\", \"right_table\": \"premises\", \"right_column\": \"upn\"}", "expected": "14"})

    -> finish({"summary": "I established that there are 14 distinct site references in the readings table that have no matching premise in the premises table, meaning all 14 site references are orphaned and do not correspond to any premise."})
