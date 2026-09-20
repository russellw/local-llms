# dictionary -- Find states no document allows

target hit: True   stopped: finish   steps: 9/10   tools: list_tables, describe_table, list_documents, read_document, distinct_values, record_finding, count_rows, finish

## step 1

    -> list_tables({})

## step 2

    -> describe_table({"table": "readings"})

## step 3

    -> list_documents({})

## step 4

    -> read_document({"name": "data-dictionary"})

## step 5

    -> distinct_values({"table": "readings", "column": "status"})

## step 6

    -> record_finding({"title": "Invalid status codes in readings.status", "evidence_tool": "distinct_values", "evidence_args": "{\"table\": \"readings\", \"column\": \"status\"}", "expected": "6"})

## step 7

    -> count_rows({"table": "readings", "column": "status", "op": "not_in", "value": "ACTUAL,ESTIMATED,CUSTOMER"})

## step 8

    -> record_finding({"title": "Invalid status codes in readings.status", "evidence_tool": "count_rows", "evidence_args": "{\"table\":\"readings\",\"column\":\"status\",\"op\":\"not_in\",\"value\":\"ACTUAL,ESTIMATED,CUSTOMER\"}", "expected": "6"})

## step 9

    -> finish({"summary": "Found 6 rows in readings.status that are not one of the three valid states defined in the data dictionary."})
