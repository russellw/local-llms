# dictionary -- Find states no document allows

target hit: True   stopped: finish   steps: 8/10   tools: list_tables, describe_table, distinct_values, list_documents, read_document, count_rows, record_finding, finish

## step 1

    -> list_tables({})

## step 2

    -> describe_table({"table": "readings"})

## step 3

    -> distinct_values({"table": "readings", "column": "status"})

## step 4

    -> list_documents({})

## step 5

    -> read_document({"name": "data-dictionary"})

## step 6

    -> count_rows({"table": "readings", "column": "status", "op": "not_in", "value": "ACTUAL,ESTIMATED,CUSTOMER"})

## step 7

    -> record_finding({"title": "The readings table contains 6 rows with a status code that is not one of the valid codes (ACTUAL, ESTIMATED, CUSTOMER).", "evidence_tool": "count_rows", "evidence_args": "{\"table\": \"readings\", \"column\": \"status\", \"op\": \"not_in\", \"value\": \"ACTUAL,ESTIMATED,CUSTOMER\"}", "expected": "6"})

## step 8

    -> finish({"summary": "I found that the readings table contains 6 rows with a status code that is not one of the valid codes (ACTUAL, ESTIMATED, CUSTOMER). This was confirmed by checking for values not in the set of permitted status codes."})
