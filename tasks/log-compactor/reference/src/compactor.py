"""Log compaction. See SPEC.md for the rules."""


def compact(records, min_count=1):
    """Reduce a record stream to the current value of each qualifying key.

    One pass, and every per-record operation is a dict lookup -- the spec's
    cost rule rules out searching the keys seen so far, which is what makes the
    obvious version quadratic. Insertion order carries the first-appearance
    ordering, so no sort is needed and none is wanted.
    """
    state = {}  # key -> [count, best_ts, value]

    for ts, key, value in records:
        slot = state.get(key)
        if slot is None:
            state[key] = [1, ts, value]
            continue
        slot[0] += 1
        # >= so that a later record wins a tie on the timestamp.
        if ts >= slot[1]:
            slot[1] = ts
            slot[2] = value

    return [
        (key, slot[2])
        for key, slot in state.items()
        if slot[0] >= min_count
    ]
