# shapes -- Count blank values in a column you can only sample

target hit: True   stopped: finish   steps: 7/8   tools: list_tables, describe_table, sample_column, distinct_values, count_rows, record_finding, finish

## step 1

    -> list_tables({})

## step 2

    -> describe_table({"table": "premises"})

## step 3

    -> sample_column({"table": "premises", "column": "address", "n": "5"})

## step 4

    -> distinct_values({"table": "premises", "column": "address"})

## step 5

    -> count_rows({"table": "premises", "column": "address", "op": "blank"})

## step 6

    -> record_finding({"title": "The premises table has 2 rows where the address field is blank.", "evidence_tool": "count_rows", "evidence_args": "{\"table\": \"premises\", \"column\": \"address\", \"op\": \"blank\"}", "expected": "2"})

## step 7

    -> finish({"summary": "I found that the premises table has 2 rows where the address field is blank, which violates the requirement that address must never be blank."})
