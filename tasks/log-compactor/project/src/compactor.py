"""Log compaction. See SPEC.md for the rules."""


def compact(records, min_count=1):
    """Reduce a record stream to the current value of each qualifying key."""
    keys = []
    counts = []
    values = []
    stamps = []

    for ts, key, value in records:
        if key in keys:
            i = keys.index(key)
            counts[i] += 1
            if ts > stamps[i]:
                stamps[i] = ts
                values[i] = value
        else:
            keys.append(key)
            counts.append(1)
            values.append(value)
            stamps.append(ts)

    out = []
    for i, key in enumerate(keys):
        if counts[i] > min_count:
            out.append((key, values[i]))
    return sorted(out)
