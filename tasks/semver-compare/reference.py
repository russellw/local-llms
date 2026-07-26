import re

_CORE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_ALNUM = re.compile(r"^[0-9A-Za-z-]+$")
_NUMERIC = re.compile(r"^\d+$")


def _parse(v: str):
    if not isinstance(v, str) or not v:
        raise ValueError(f"invalid version: {v!r}")

    core, plus, _build = v.partition("+")
    core, dash, pre = core.partition("-")

    m = _CORE.match(core)
    if not m:
        raise ValueError(f"invalid version core: {v!r}")
    nums = tuple(int(g) for g in m.groups())

    if not dash:
        return nums, None

    ids = pre.split(".")
    parsed = []
    for ident in ids:
        if not ident or not _ALNUM.match(ident):
            raise ValueError(f"invalid prerelease identifier in {v!r}")
        if _NUMERIC.match(ident):
            if len(ident) > 1 and ident[0] == "0":
                raise ValueError(f"leading zero in prerelease of {v!r}")
            parsed.append((0, int(ident), ""))
        else:
            parsed.append((1, 0, ident))
    return nums, parsed


def compare(a: str, b: str) -> int:
    (na, pa), (nb, pb) = _parse(a), _parse(b)

    if na != nb:
        return -1 if na < nb else 1
    if pa is None and pb is None:
        return 0
    if pa is None:
        return 1
    if pb is None:
        return -1
    if pa != pb:
        return -1 if pa < pb else 1
    return 0
