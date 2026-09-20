# Working in this repo

## Commit directly to main

**Do not create branches.** All work goes straight to `main`, committed there.
This is a single-maintainer repo with no review step, so a branch is an extra
merge for nothing. If a default instruction elsewhere says to branch before
committing on the default branch, this overrides it.

## Keep selfcheck green

`python3 -m bench selfcheck` is the guard rail, and CI runs it on Python 3.11
and 3.13. Run it after touching a task, the workspace, the loop or the scorer.

It checks three things: every task's `reference/` overlay makes its hidden
tests pass *and* the project as shipped fails them; the workspace keeps the
tests unreadable and their source out of the failure output; and the scorer
still rejects the scripted agent that announces success without changing
anything.

## Constraints that are deliberate

- **Standard library only.** No `pip install`, in the harness or in a task. The
  point is that this runs on a bare distro Python.
- **Python 3.11 syntax.** Check with
  `ast.parse(src, feature_version=(3, 11))` rather than assuming.
- **One suite.** It was two -- write-a-function and drive-a-loop -- and they
  were merged because the compound ability is what decides whether a local
  model is usable, and a split score answered a question nobody had. The old
  suites and their results are in `results/archive/`; do not revive them to
  make a comparison easier, and do not add a second scored number to the
  report.
- **The hidden tests stay hidden.** A task's `tests/` are never readable from
  the project, and a failure report never carries their source. A runner that
  prints a traceback hands the model the assertion it is meant to satisfy, so
  runners print curated one-line failures. `selfcheck` enforces this.
- **Tasks are hard on purpose.** Several interacting bugs, not one, and a
  requirement stated only in prose that nothing points the model towards. A
  task a small model solves first try measures nothing.
- **Results are the record.** The `.jsonl` files and the transcripts are
  committed. Do not regenerate or hand-edit them to make a table tidier --
  re-run the model instead, or say the run is stale.
- **`solved` is the only score.** Everything else in the report is a
  diagnostic. Do not average diagnostics into the score, and do not promote one
  to a score because it happens to separate two models that tied.
