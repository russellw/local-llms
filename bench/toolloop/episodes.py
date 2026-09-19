"""The four episodes, and what each one is trying to separate.

Each episode is a brief and a target. The target is expressed as a *query* --
the tool call whose result establishes the defect -- and never as text, so
scoring never depends on reading what the model wrote. A finding counts when
the query it carries is about the right column and returns the right number.

The axes are taken from a real comparison of five models on an agentic data
audit, where the tiers separated on four things and none of them was coding
ability:

    operates the tools | not confused by shapes | asks the right question |
    seeks out information

`basics` probes the first, `shapes` the second, all four probe the third, and
`dictionary` and `premise` probe the fourth.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Target:
    """What a finding has to carry to count. Text is never consulted."""

    mentions: list[str]  # "table.column" pairs the evidence call must reference
    value: str  # the number the evidence must return
    tool: str | None = None  # constrain the evidence tool, when it matters


@dataclass
class Episode:
    id: str
    title: str
    axis: str
    brief: str
    target: Target
    budget: int = 10
    max_tokens: int = 384
    documents_relevant: bool = False
    anti_target: Target | None = None
    anti_note: str = ""


_PREAMBLE = """\
You are auditing a dataset for defects. The data stays where it is: you
investigate it through the tools, and the tools are the only way to see it.

Two things about this dataset. Columns that hold many distinct values cannot be
returned verbatim -- sampling one gives you its *shape* instead. And the
customer supplied documents alongside the data; they are listed by
list_documents and are part of the dataset, not background reading.

Record what you establish with record_finding, then call finish. A finding is
re-run before it is kept, so claim only what your query actually returns.
"""

EPISODES: list[Episode] = [
    Episode(
        id="basics",
        title="Find the impossible values in a numeric column",
        axis="mechanics",
        brief=_PREAMBLE
        + """
Your target: `readings.kwh` records consumption since the previous reading, so
it can never be negative. Establish how many rows violate that, record it, and
finish.
""",
        target=Target(mentions=["readings.kwh"], value="3"),
        budget=8,
    ),
    Episode(
        id="shapes",
        title="Count blank values in a column you can only sample",
        axis="shapes",
        brief=_PREAMBLE
        + """
Your target: `premises.address` is hand-entered and is never allowed to be
blank. Establish how many rows are blank, record it, and finish.
""",
        target=Target(mentions=["premises.address"], value="2"),
        budget=8,
    ),
    Episode(
        id="dictionary",
        title="Find states no document allows",
        axis="right-question",
        brief=_PREAMBLE
        + """
Your target: `readings.status` is a coded column, and the export is supposed to
use only the states this dataset defines as valid. Establish how many rows
carry a state that is not one of them, record it, and finish.
""",
        target=Target(mentions=["readings.status"], value="6"),
        budget=10,
        documents_relevant=True,
    ),
    Episode(
        id="premise",
        title="A join that only holds after a documented rule is applied",
        axis="right-question",
        brief=_PREAMBLE
        + """
Your target: every reading is supposed to belong to a premise.
`readings.site_ref` is the reference, `premises.upn` is what it points at.
Establish how many distinct site references have no premise, record it, and
finish.
""",
        target=Target(
            mentions=["readings.site_ref", "premises.upn"],
            value="4",
            tool="check_orphans",
        ),
        anti_target=Target(
            mentions=["readings.site_ref", "premises.upn"],
            value="14",
            tool="check_orphans",
        ),
        anti_note=(
            "reported 14 orphans: the correct count for the query it wrote, and "
            "the wrong question. Re-running the evidence cannot catch this"
        ),
        budget=12,
        documents_relevant=True,
    ),
]


def load_episodes(filters: list[str] | None = None) -> list[Episode]:
    eps = list(EPISODES)
    if filters:
        eps = [e for e in eps if any(f in (e.id, e.axis) for f in filters)]
    return eps
