# premise -- A join that only holds after a documented rule is applied

target hit: False   stopped: finish   steps: 3/12   tools: check_orphans, record_finding, finish

## step 1

    -> check_orphans({"left_table": "readings", "left_column": "site_ref", "right_table": "premises", "right_column": "upn"})

## step 2

    -> record_finding({"title": "All site references in readings have no matching premise", "evidence_tool": "check_orphans", "evidence_args": "{\"left_table\":\"readings\",\"left_column\":\"site_ref\",\"right_table\":\"premises\",\"right_column\":\"upn\"}", "expected": "14"})

## step 3

    -> finish({"summary": "All 14 distinct site references in readings have no matching premise."})
