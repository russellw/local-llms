# shapes -- Count blank values in a column you can only sample

target hit: True   stopped: finish   steps: 5/8   tools: list_tables, count_rows, record_finding, finish

## step 1

    -> list_tables({})

## step 2

    -> count_rows({"table": "premises", "column": "address", "op": "blank"})

## step 3

    -> record_finding({"title": "premises.address contains blank values", "evidence_tool": "count_rows", "evidence_args": "{\"table\": \"premises\", \"column\": \"address\", \"op\": \"blank\"}", "expected": "0"})

## step 4

    -> record_finding({"title": "premises.address contains blank values", "evidence_tool": "count_rows", "evidence_args": "{\"table\":\"premises\",\"column\":\"address\",\"op\":\"blank\"}", "expected": "2"})

## step 5

    -> finish({"summary": "premises.address has 2 blank rows"})
