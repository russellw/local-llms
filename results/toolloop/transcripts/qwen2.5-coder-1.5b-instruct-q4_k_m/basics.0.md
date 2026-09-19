# basics -- Find the impossible values in a numeric column

target hit: False   stopped: finish   steps: 2/8   tools: count_rows, finish

## step 1

```json
{
  "name": "count_rows",
  "arguments": {
    "table": "readings.kwh",
    "column": "kwh",
    "op": "<",
    "value": "0"
  }
}
```

    -> count_rows({"table": "readings.kwh", "column": "kwh", "op": "<", "value": "0"})

## step 2

```json
{
  "name": "finish",
  "arguments": {
    "summary": "There are no rows in the 'readings.kwh' table that violate the condition 'kwh < 0'."
  }
}
```

    -> finish({"summary": "There are no rows in the 'readings.kwh' table that violate the condition 'kwh < 0'."})
