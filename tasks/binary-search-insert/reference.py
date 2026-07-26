def insert_position(seq, x, side: str = "left") -> int:
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")
    lo, hi = 0, len(seq)
    while lo < hi:
        mid = (lo + hi) // 2
        before = seq[mid] <= x if side == "right" else seq[mid] < x
        if before:
            lo = mid + 1
        else:
            hi = mid
    return lo
