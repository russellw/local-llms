def parse_csv(text: str) -> list[list[str]]:
    if not text:
        return []

    rows: list[list[str]] = []
    row: list[str] = []
    field: list[str] = []
    in_quotes = False
    at_field_start = True
    ended_record = False  # did the input stop right after a record separator?
    i = 0
    n = len(text)

    def end_field():
        nonlocal field, at_field_start
        row.append("".join(field))
        field = []
        at_field_start = True

    while i < n:
        ch = text[i]
        ended_record = False

        if in_quotes:
            if ch == '"':
                if i + 1 < n and text[i + 1] == '"':
                    field.append('"')
                    i += 2
                    continue
                in_quotes = False
                at_field_start = False
                i += 1
                continue
            field.append(ch)
            i += 1
            continue

        if ch == '"' and at_field_start:
            in_quotes = True
            at_field_start = False
            i += 1
            continue

        if ch == ",":
            end_field()
            i += 1
            continue

        if ch in "\r\n":
            end_field()
            rows.append(row)
            row = []
            ended_record = True
            if ch == "\r" and i + 1 < n and text[i + 1] == "\n":
                i += 2
            else:
                i += 1
            continue

        field.append(ch)
        at_field_start = False
        i += 1

    if in_quotes:
        raise ValueError("unterminated quoted field")

    # A trailing separator already flushed the last record; don't invent another.
    if not ended_record:
        end_field()
        rows.append(row)
    return rows
