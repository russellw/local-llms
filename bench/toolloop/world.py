"""The dataset a tool-loop episode runs against, and the tools over it.

Deliberately tiny and entirely deterministic: no database, no files, no RNG.
Every number the scorer expects is derivable from the literals below, and
`bench selfcheck` re-derives them, so a careless edit here fails CI rather than
silently changing what the models are being asked.

The shape is copied from a real dataset audit (a metering export joined to a
premises register), because the failure modes worth measuring are the ones that
showed up there:

  * a foreign key that only joins after a documented prefix is stripped,
  * a status column with states no document allows,
  * sampled values that arrive as *shapes* rather than contents, because the
    egress guard rewrote them on the way out.

That last one matters more than it looks. A model that reads `AAAA 9999` as
something it can search for will spend its whole budget querying for a string
that is not in the data, and no amount of coding ability prevents it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# --- the data ---------------------------------------------------------------
#
# 14 distinct site references, 10 of which have a matching premise once the
# decorative prefixes come off. Four do not, and those four are the answer.

_SITE_SUFFIXES = [1001 + i for i in range(14)]
_PREMISE_SUFFIXES = _SITE_SUFFIXES[:10] + [2020, 2021]

_VALID_STATUS = ["ACTUAL", "ESTIMATED", "CUSTOMER"]
# Six rows carry a state no document allows. Six rather than five so that the
# answer differs from the number of *distinct* states (five), which would
# otherwise let a model reach the right number by the wrong reasoning and score
# the initiative axis by luck.
_BAD_STATUS = {3: "EST", 11: "EST", 22: "EST", 35: "EST", 17: "A", 29: "A"}
_NEGATIVE_KWH = {7, 19, 31}
_REGIONS = ["North West", "South East", "Midlands", "North East"]


def _readings() -> list[dict]:
    rows = []
    for i in range(40):
        kwh = round(120.0 + 7.5 * (i % 11), 1)
        if i in _NEGATIVE_KWH:
            kwh = -kwh
        rows.append(
            {
                "reading_id": f"R{4000 + i}",
                "site_ref": f"SITE-{_SITE_SUFFIXES[i % 14]}",
                "taken_on": f"2026-0{1 + i % 6}-{10 + i % 18:02d}",
                "kwh": kwh,
                "status": _BAD_STATUS.get(i, _VALID_STATUS[i % 3]),
            }
        )
    return rows


def _premises() -> list[dict]:
    rows = []
    for i, suffix in enumerate(_PREMISE_SUFFIXES):
        address = f"{10 + i} Example Street, Unit {i}"
        if i == 4:
            address = ""
        elif i == 9:
            address = "   "
        rows.append(
            {
                "upn": f"UPN-{suffix}",
                "address": address,
                "region": _REGIONS[i % 4],
            }
        )
    return rows


TABLES: dict[str, list[dict]] = {
    "readings": _readings(),
    "premises": _premises(),
}

# Columns whose contents may be returned verbatim. Everything else can only be
# sampled, and sampling returns shapes. This mirrors an egress guard: the point
# is not secrecy inside the benchmark, it is that the model meets redacted data
# and has to notice what it is looking at.
LOW_CARDINALITY = {("readings", "status"), ("premises", "region")}

DOCUMENTS: dict[str, tuple[str, str]] = {
    "data-dictionary": (
        "Field definitions for the metering export.",
        """# Data dictionary -- metering export

## readings.site_ref and premises.upn

These are the same identifier under two names. The field collection app writes
site references with a `SITE-` prefix; the billing system writes the same
number into `premises.upn` with a `UPN-` prefix. **Both prefixes are
decorative.** A reading belongs to a premise when the digits after the hyphen
are equal.

Comparing the two columns as written reports every reading as an orphan, which
is a property of the prefixes and not of the data.

## readings.status

Exactly three states are permitted in this export:

  - `ACTUAL`    -- read from the meter
  - `ESTIMATED` -- interpolated by the billing system
  - `CUSTOMER`  -- submitted by the customer

Any other value is a defect. Abbreviations were used by an older version of the
collection app and were supposed to have been migrated.

## readings.kwh

Consumption since the previous reading. Never negative; a negative value means
the register rolled over and was not corrected.

## premises.address

Free text, entered by hand, not validated. Blank is a known defect.
""",
    ),
    "ticket-4482": (
        "Support ticket about a slow report screen.",
        """# TICKET-4482 -- Consumption report takes 40 seconds to load

Reported by the billing team. The monthly consumption screen spins for about
40 seconds before rendering. Not a data problem; the report runs three
unindexed scans and someone should add the index. Assigned to platform.

No action required on the export itself.
""",
    ),
    "onboarding-note": (
        "How the export is produced each month.",
        """# Monthly export

The export is produced on the first working day of the month by the scheduled
job `meter-export`. It writes `readings.csv` and `premises.csv` into the
handover bucket. The job has not changed since 2024.
""",
    ),
}


# --- guard errors -----------------------------------------------------------

_SHAPE_RE = re.compile(r"^[AaXx9#]{2,}([ \-/][AaXx9#]{2,})*$")


class ToolError(Exception):
    """A tool refused the call. The message is what the model sees."""


def _shape_of(value: str) -> str:
    """Rewrite a value as its form: letters to A, digits to 9, case preserved."""
    out = []
    for ch in str(value):
        if ch.isdigit():
            out.append("9")
        elif ch.isalpha():
            out.append("A" if ch.isupper() else "a")
        else:
            out.append(ch)
    return "".join(out)


def looks_like_shape(value: str) -> bool:
    """True if the model is searching for a redaction rather than a value."""
    v = str(value).strip()
    if len(v) < 2:
        return False
    return bool(_SHAPE_RE.match(v))


# --- helpers ----------------------------------------------------------------


def _table(name: str) -> list[dict]:
    key = str(name).strip().lower()
    if key not in TABLES:
        raise ToolError(
            f"no table named {name!r}; tables are: {', '.join(sorted(TABLES))}"
        )
    return TABLES[key]


def _column(table: str, column: str) -> str:
    rows = _table(table)
    key = str(column).strip().lower()
    cols = list(rows[0].keys())
    if key not in cols:
        raise ToolError(
            f"no column {column!r} on {table}; columns are: {', '.join(cols)}"
        )
    return key


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _as_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _split_list(value: str) -> list[str]:
    return [p.strip() for p in str(value).split(",") if p.strip()]


# --- the tools --------------------------------------------------------------
#
# Every tool takes strings and returns a short JSON string. Strings throughout
# because a 4B model asked for a typed array will hand you a stringified one
# about half the time, and that is not the thing being measured here.


def list_tables() -> str:
    return json.dumps(
        {"tables": [{"name": n, "rows": len(r)} for n, r in sorted(TABLES.items())]}
    )


def describe_table(table: str) -> str:
    rows = _table(table)
    cols = []
    for c in rows[0]:
        distinct = len({str(r[c]) for r in rows})
        cols.append(
            {
                "name": c,
                "distinct": distinct,
                "samplable_verbatim": (str(table).strip().lower(), c)
                in LOW_CARDINALITY,
            }
        )
    return json.dumps({"table": str(table).strip().lower(), "rows": len(rows), "columns": cols})


def sample_column(table: str, column: str, n: str = "8") -> str:
    col = _column(table, column)
    rows = _table(table)
    limit = int(_as_float(n) or 8)
    shapes, seen = [], set()
    for r in rows:
        s = _shape_of(r[col])
        if s not in seen:
            seen.add(s)
            shapes.append(s)
        if len(shapes) >= max(1, limit):
            break
    return json.dumps(
        {
            "table": str(table).strip().lower(),
            "column": col,
            "distinct_values": len({str(r[col]) for r in rows}),
            "note": "values are redacted to shapes: A=letter, 9=digit, other characters literal",
            "shapes": shapes,
        }
    )


def distinct_values(table: str, column: str) -> str:
    col = _column(table, column)
    key = (str(table).strip().lower(), col)
    if key not in LOW_CARDINALITY:
        raise ToolError(
            f"{key[0]}.{col} may not be returned verbatim (too many distinct values "
            f"to be safe to release). Use sample_column for its shape, or count_rows "
            f"to test a hypothesis about it."
        )
    rows = _table(table)
    counts: dict[str, int] = {}
    for r in rows:
        counts[str(r[col])] = counts.get(str(r[col]), 0) + 1
    return json.dumps(
        {"table": key[0], "column": col, "values": [{"value": v, "rows": c} for v, c in sorted(counts.items())]}
    )


_OPS = {"=", "!=", "<", ">", "<=", ">=", "blank", "not_blank", "in", "not_in"}


def count_rows(table: str, column: str, op: str, value: str = "") -> str:
    col = _column(table, column)
    rows = _table(table)
    o = str(op).strip().lower()
    if o in ("==", "eq"):
        o = "="
    if o in ("ne", "<>"):
        o = "!="
    if o not in _OPS:
        raise ToolError(f"unknown op {op!r}; ops are: {', '.join(sorted(_OPS))}")

    if o not in ("blank", "not_blank") and looks_like_shape(value):
        raise ToolError(
            f"{value!r} is a value *shape*, not a value. Shapes describe the form "
            f"of the data (A=letter, 9=digit) and never occur in it, so this "
            f"comparison would always be false. Use distinct_values for a column "
            f"that allows it, or test a hypothesis you formed some other way."
        )

    n = 0
    for r in rows:
        v = r[col]
        if o == "blank":
            ok = _blank(v)
        elif o == "not_blank":
            ok = not _blank(v)
        elif o == "in":
            ok = str(v) in _split_list(value)
        elif o == "not_in":
            ok = str(v) not in _split_list(value)
        else:
            fv, fx = _as_float(v), _as_float(value)
            if fv is not None and fx is not None:
                ok = {
                    "=": fv == fx,
                    "!=": fv != fx,
                    "<": fv < fx,
                    ">": fv > fx,
                    "<=": fv <= fx,
                    ">=": fv >= fx,
                }[o]
            else:
                sv, sx = str(v), str(value)
                ok = {
                    "=": sv == sx,
                    "!=": sv != sx,
                    "<": sv < sx,
                    ">": sv > sx,
                    "<=": sv <= sx,
                    ">=": sv >= sx,
                }[o]
        n += bool(ok)
    return json.dumps({"table": str(table).strip().lower(), "column": col, "op": o, "value": value, "count": n})


def check_orphans(
    left_table: str,
    left_column: str,
    right_table: str,
    right_column: str,
    left_strip: str = "",
    right_strip: str = "",
) -> str:
    lc = _column(left_table, left_column)
    rc = _column(right_table, right_column)

    def norm(v, prefix):
        s = str(v)
        p = str(prefix or "")
        return s[len(p):] if p and s.startswith(p) else s

    left = {norm(r[lc], left_strip) for r in _table(left_table)}
    right = {norm(r[rc], right_strip) for r in _table(right_table)}
    orphans = sorted(left - right)
    return json.dumps(
        {
            "left": f"{str(left_table).strip().lower()}.{lc}",
            "right": f"{str(right_table).strip().lower()}.{rc}",
            "left_strip": left_strip,
            "right_strip": right_strip,
            "distinct_left_values": len(left),
            "orphans": len(orphans),
            "examples": orphans[:5],
        }
    )


def list_documents() -> str:
    return json.dumps(
        {"documents": [{"name": n, "about": d[0]} for n, d in sorted(DOCUMENTS.items())]}
    )


def read_document(name: str) -> str:
    key = str(name).strip().lower()
    if key not in DOCUMENTS:
        raise ToolError(
            f"no document named {name!r}; documents are: {', '.join(sorted(DOCUMENTS))}"
        )
    return DOCUMENTS[key][1]


# Tools that answer a question about the data, and so may serve as evidence for
# a finding. record_finding re-runs one of these and checks the model's claim.
EVIDENCE_TOOLS = {
    "count_rows": count_rows,
    "check_orphans": check_orphans,
    "distinct_values": distinct_values,
}

READ_TOOLS = {
    "list_tables": list_tables,
    "describe_table": describe_table,
    "sample_column": sample_column,
    "list_documents": list_documents,
    "read_document": read_document,
    **EVIDENCE_TOOLS,
}


# --- canonical calls --------------------------------------------------------


def canonical(tool: str, args: dict) -> tuple:
    """A normalised (tool, args) pair, for comparing a call to an expectation.

    Scoring keys off this rather than off anything the model wrote in prose.
    Whether a finding is *about* the right thing is decided by the query it
    carries, which is machine-readable; its title is not scored at all.
    """
    norm = {}
    for k, v in (args or {}).items():
        k = str(k).strip().lower()
        s = str(v).strip()
        if k in ("table", "column", "left_table", "left_column", "right_table", "right_column", "op"):
            s = s.lower()
        if k == "op":
            s = {"==": "=", "eq": "=", "ne": "!=", "<>": "!="}.get(s, s)
        if k == "value" and "," in s:
            s = ",".join(sorted(p.strip() for p in s.split(",") if p.strip()))
        if k == "n":
            continue  # sample size is not part of what a call means
        norm[k] = s
    return (str(tool).strip().lower(), tuple(sorted(norm.items())))


def values_equal(claimed, actual) -> bool:
    """Compare a model's claimed number to the real one, leniently about type."""
    a, b = _as_float(claimed), _as_float(actual)
    if a is not None and b is not None:
        return abs(a - b) < 1e-9
    return str(claimed).strip().lower() == str(actual).strip().lower()


def result_value(tool: str, payload: str):
    """The single number a model is claiming when it cites this tool."""
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload
    for key in ("count", "orphans"):
        if key in data:
            return data[key]
    if "values" in data:  # distinct_values: the claim is how many there are
        return len(data["values"])
    return payload
