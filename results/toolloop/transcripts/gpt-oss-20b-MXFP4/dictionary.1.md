# dictionary -- Find states no document allows

target hit: True   stopped: finish   steps: 7/10   tools: list_tables, describe_table, list_documents, read_document, count_rows, record_finding, finish

## step 1

    -> list_tables({})

## step 2

    -> describe_table({"table": "premises"})

## step 3

    -> list_documents({})

## step 4

    -> read_document({"name": "data-dictionary"})

## step 5

    -> count_rows({"table": "readings", "column": "status", "op": "not_in", "value": "ACTUAL,ESTIMATED,CUSTOMER"})

## step 6

    -> record_finding({"title": "Invalid status codes in readings.status", "evidence_tool": "count_rows", "evidence_args": "{\"table\": \"readings\", \"column\": \"status\", \"op\": \"not_in\", \"value\": \"ACTUAL,ESTIMATED,CUSTOMER\"}", "expected": "6"})

## step 7

    -> finish({"summary": "Found 6 rows in readings.status with values outside the allowed set of ACTUAL, ESTIMATED, CUSTOMER."})
