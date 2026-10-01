# local-llms

[![selfcheck](https://github.com/russellw/local-llms/actions/workflows/selfcheck.yml/badge.svg)](https://github.com/russellw/local-llms/actions/workflows/selfcheck.yml)

Benchmarking locally-runnable LLMs on ordinary CPU hardware, on the only
question that turns out to matter: **can it do a real piece of coding work by
itself?**

Every model here runs on the machine in front of you: no GPU, no API key, no
data leaving the box.

## What it measures

One suite. Each task is a small Python project that does not pass its tests,
and **two** test suites:

- one the model **cannot read but can run as often as it likes**, which reports
  the symptoms;
- one it never sees, never runs, and is scored on, which checks the rules that
  are stated only in the project's spec.

The model gets six tools -- list, read, write, targeted replace, run the tests,
stop -- and a step budget. It passes when the **held-out** suite passes against
whatever it left on disk.

That split is the point of the design. A model can satisfy every signal it has
access to and still be wrong, and the gap between the two suites is the
`green but wrong` column. This is how real work fails: the tests pass and
production breaks, because the tests described the symptom and the requirement
lived somewhere nobody read.

It exists because the first version of this suite had only the runnable half,
and a 20B model solved every task on every attempt. A suite a model can run to
completion measures how well it hill-climbs a gradient you handed it. The
weaker the model, the more it leans on that: on the runnable-only version the
strongest model needed 2.1 test runs per attempt and the weakest 8.8. Removing
the gradient is the only change that makes the question *why is this wrong*
unavoidable.

That is deliberately one task and not two, because it is the compound ability
that decides whether a local model is any use:

| it has to | or it fails by |
|---|---|
| operate the tools at all | writing calls as prose nobody executes |
| navigate code it did not write | editing the wrong file, or guessing at a function it never read |
| work out what is actually wrong | fixing the symptom the first failure names and stopping |
| write correct, non-trivial Python | passing eleven of twelve and calling it done |
| check itself | declaring victory over a suite that is still red |

Earlier versions of this repo split that into a write-a-function suite and a
drive-a-loop suite. Both are in `results/archive/`, along with what they
measured. They were separated because the abilities fail in different places,
and merged again because a model that has one and not the other is not usable
either way, so a table with two columns and a footnote was answering a question
nobody had.

The tok/s figures sit alongside the scores, because on this hardware **too slow
to use** is its own way to be unusable.

## The machine

| | |
|---|---|
| CPU | Intel i5-7300U, 2 physical cores / 4 threads, AVX2 |
| RAM | 30 GB usable |
| GPU | none |
| Effective memory bandwidth | ~14 GB/s (measured, see below) |

That bandwidth number is the one that matters. CPU token generation is
memory-bound: every generated token requires reading the model's active weights
out of RAM, so **tokens/sec ≈ bandwidth ÷ active-weight bytes**. Compute barely
enters into it.

Two consequences shape every model choice in this repo:

1. **RAM capacity is not the constraint; bandwidth is.** 30 GB is enough to
   *load* a 30B dense model at Q4, but reading ~18 GB per token caps you near
   0.8 tok/s. A 500-token answer would take ten minutes.
2. **Mixture-of-experts models are the sweet spot.** An MoE only reads its
   *active* parameters per token. Qwen3-Coder-30B-A3B has 30B total parameters
   but ~3B active, so it carries a 30B model's knowledge at roughly a 3B
   model's speed. On this box that is the difference between unusable and
   usable.

An agentic suite is far more sensitive to this than a single-shot one. A task
here is twenty-odd model turns, each replaying a conversation that grows with
every file read, so prompt processing stops being a rounding error and starts
being most of the wall clock.

## Quick start

```bash
scripts/build.sh                     # build llama.cpp (slow: ~15 min on 2 cores)
scripts/fetch-model.sh mistralai/Devstral-Small-2507_gguf \
    Devstral-Small-2507-Q4_K_M.gguf

scripts/serve.sh models/Devstral-Small-2507-Q4_K_M.gguf   # terminal 1
python3 -m bench run --label devstral-small-2507-q4       # terminal 2
```

Start with a single task -- `--task inventory-ledger` -- to see what the loop
looks like before committing to a full run.

No `pip install`: the harness is standard library only, so it runs on a bare
Python 3.11+.

## Commands

| Command | What it does |
|---|---|
| `python3 -m bench tasks` | list the tasks |
| `python3 -m bench selfcheck` | prove the suite still measures what it claims |
| `python3 -m bench run --label NAME` | run the suite against the served model |
| `python3 -m bench report --write` | regenerate `results/REPORT.md` from all runs |

Useful `run` flags: `--task <id>` (repeatable) to run a subset, `--repeats N`
to sample each task N times, `--protocol native|text|auto`, `--fresh` to
discard prior results, `--max-tokens-scale 3` for a reasoning model that needs
room to think before each call.

Runs default to temperature 0. That is the right setting for a single pass --
greedy decoding is deterministic, so the score is reproducible. It is the wrong
setting for `--repeats > 1`, where every attempt would replay the identical
run, so passing repeats without a temperature switches to 0.2 and says so.

**`selfcheck` is the guard rail**, and it is the thing to run after touching a
task, the workspace or the scorer. It checks three things:

- **Every task is solvable and not already solved.** Its `reference/` overlay
  must make the hidden suite pass, and the project as shipped must fail it. A
  task whose own reference fix fails measures nothing; a task that passes as
  shipped measures nothing either, and both are easy to introduce by accident.
  It has already caught a test of mine that was wrong rather than a reference
  that was.
- **The workspace cannot be talked out of its boundaries.** The tests must not
  be readable, reachable by a relative path, or visible in a listing, and
  failure output must not carry their source back to the model.
- **The scorer scores the right thing.** Scripted agents are played against it:
  one that applies the reference fix must pass, one that announces success
  without changing anything must not, one that gets the suite green and then
  breaks it again must be scored on the wreckage, and one whose every call is
  written as prose must fail the tool-operating floor.

## The tasks

Five, all deliberately hard. A task that a 7B solves on the first try tells you
nothing you did not already know.

| Task | The work | The trap |
|---|---|---|
| `inventory-ledger` | FIFO stock costing with fractional unit costs | rounding each lot separately instead of once per issue -- and the rule is stated only in `README.md` |
| `route-matcher` | URL routing with parameter and wildcard segments | matching in registration order, when the spec decides by segment specificity |
| `log-compactor` | one-pass compaction of a record stream | fixing the logic and leaving the per-record scan, so it stays quadratic and the suite times out |
| `retry-policy` | backoff, jitter, throttling and an elapsed budget | fixing the arithmetic while the classifier still calls `429` fatal, so the throttling branch is never reached |
| `crash-recovery` | rebuilding a store from a checkpoint and a damaged journal | skipping a corrupt record and carrying on, where the spec says replay stops there and discards everything after |

`crash-recovery` is the hardest and was added because gpt-oss-20b solved the
other four outright. Its three bugs are spread over three files and none of
them is local to the symptom: replay is off by one against the checkpoint's own
sequence number, recovery aliases the checkpoint's state instead of copying it
(so recovering twice gives different answers), and a corrupt record is skipped
rather than stopping the replay. Fixing everything visible in the code gets to
**18 of 20** and still fails -- the last two need the rule that exists only in
`SPEC.md`.

Each has several interacting bugs rather than one, because a single planted bug
rewards pattern-matching and a spec clause nobody mentioned rewards reading.
Each carries a requirement that **cannot be inferred from the code** -- stated
in a `README.md` or `SPEC.md` that nothing points the model towards. Whether it
goes and reads that file is its own column in the report.

**How much the tests give away, stated honestly.** A failing assertion has to
report what it expected, so the *target values* are visible: a model that reads
`expected 'throttled'` knows what 429 should classify as. What it does not get
is the *reason* -- it must still infer "round half to even" from "expected 2,
not 3", and the spec is where the reasons are.

That boundary was not free. The first version of this suite named its checks
after the rules they enforced -- `rounds_once_not_per_lot`,
`static_beats_param_registered_later`,
`everything_after_a_corrupt_record_is_discarded_too` -- and printed those names
on failure. The specs were therefore readable straight off the test output, and
two models solved `crash-recovery` without opening `SPEC.md` at all. Checks are
now named for the scenario they run, not the rule they check.

### Adding a task

```
tasks/<id>/
    task.json     title, brief, budget, difficulty, spec_file
    project/      the tree the model is given, copied fresh per attempt
    tests/        run_tests.py -- runnable by the model, never readable
    acceptance/   run_tests.py -- held out; the suite the score comes from
    reference/    files overlaid on project/ to make both suites pass
```

**Design the split deliberately.** `tests/` must fail as shipped, or the model
has nothing to work from and stops at once. `acceptance/` must hold the rules
that only the spec states, so that a fix arrived at by watching the visible
tests go green is not enough. The test worth running by hand: build the
reference, put the spec-only rules back to their broken state, and check that
the visible suite goes green while the held-out one does not. All five tasks
here satisfy that, and `crash-recovery` needed a mechanical bug added
afterwards because all three of its original bugs were spec-only -- its visible
suite passed as shipped, which would have made it unplayable.

`tests/run_tests.py` must print `RESULT <n> passed <m> failed` and exit
non-zero on failure. Print **curated one-line failures and never a traceback**:
a traceback quotes the failing source line, which for a hidden suite hands the
model the assertion it is supposed to satisfy.

**Name checks after the scenario, not the rule.** `two_lots_of_half_a_cent`,
not `rounds_once_not_per_lot`; `delay_on_attempt_6_with_a_cap_of_10`, not
`the_ceiling_is_capped_before_jitter`. The same goes for the text in an
assertion: report the quantity that differs ("cost of issuing 2"), not the
policy it should have followed ("cost of two half-cent units rounded once").
The check name is printed to the model on every failing run, so a descriptive
one is a free copy of the spec and makes the `reads the spec` column measure
nothing. This is the single easiest way to ruin a task, and it ruined all five
of these before it was noticed.

Then run `python3 -m bench selfcheck`.

## What this does not measure

Stated plainly, because these are deliberate boundaries rather than oversights:

**Five tasks is a small sample.** It resolves large differences between models
and nothing finer. Attempts at the same task are correlated, so the effective
sample size is closer to the number of *tasks* than the number of attempts.

**The projects are small and synthetic.** A few files each, written to be
broken in specific ways. That is what makes them deterministic, replayable and
free of contamination, and it is also why passing here is not evidence a model
can work in a real repository with a hundred thousand lines and no spec.

**Whole-file writes and exact-string replaces are not a real editor.** No
patches, no partial application, no failure to apply. A model that is good at
producing diffs gets no credit for it, and one that is bad at it is not
punished.

**One hardware configuration, one quantisation.** Results are Q4_K_M (or the
model's native format) on one CPU. Quantisation quality effects and any
GPU-relevant conclusions are out of scope; the tok/s figures transfer to
nothing but a machine with similar memory bandwidth.

**Contamination is damped, not absent.** The projects are written for this
repo, so they are not in any model's training data today. Nothing stops that
changing, and the defence is that they are cheap to replace.

**All five tasks are solvable and none is saturated.** gpt-oss-20b has solved
each of the five at least once against the held-out suite, so a zero is the
model's rather than the task's. It has also failed four of the fifteen, so no
task is free.

The ceiling is no longer the problem; the floor might be. Three models score
zero across five tasks, which orders them not at all -- `tests green`,
`green but wrong` and `reads the spec` are what separate them, and they are
diagnostics rather than a score. If the point is to rank models below
gpt-oss-20b, this suite needs an easier tier more than a harder one. The 7% of
Qwen3.6-35B-A3B is the first row to land between the two groups, and it took a
model that reads the spec and then ignores what it read to get there.

## What the runs found

Six models, on the machine described above. `results/REPORT.md` has the full
table; this is the part worth knowing.

| Model | solved | tests green | any | reads the spec | green but wrong | tok/s |
|---|---|---|---|---|---|---|
| gpt-oss-20b-MXFP4 | **73%** | 100% | 100% | 87% | 4 | 1.9 |
| Qwen3.6-27B | **73%** | 100% | 80% | 100% | 4 | 0.6 |
| Qwen3.6-35B-A3B | **7%** | 80% | 20% | 73% | 11 | 3.4 |
| Devstral-Small-2507 | **0%** | 60% | 0% | 20% | 3 | 0.6 |
| Qwen3-Coder-30B-A3B | **0%** | 40% | 0% | 80% | 6 | 1.2 |
| Qwen2.5-Coder-32B | **0%** | 20% | 0% | 0% | 1 | 0.4 |

gpt-oss-20b, Qwen3-Coder-30B-A3B, Qwen3.6-27B and Qwen3.6-35B-A3B ran three
attempts per task, Devstral and Qwen2.5-Coder one, because at 0.4 tok/s a
single pass is most of a day.

**Two models solve anything at all, and they tie.** Three of the five score
zero across five tasks, and the column that explains it is `tests green`: every
model satisfies far more of what it can see than it actually gets right.
gpt-oss goes green on 100% of visible suites and is wrong on a quarter of them.
Qwen3-Coder goes green on 40% and right on none.

**The tie is not a coincidence of rounding, and it hides a real difference.**
Both models solve 11 of 15 attempts, with the same `green but wrong` count and
no false-dones between them. They fail in different places. gpt-oss eventually
solves all five tasks (`any` 100%) and its four failures are scattered.
Qwen3.6-27B solves `crash-recovery` 3 for 3 -- the task added because gpt-oss
had saturated the other four -- and fails `inventory-ledger` 0 for 3, every
time at 2 of 7 held-out checks and 8 of 26 steps. That is a reproducible blind
spot rather than variance: it opens the `README.md` holding the rule on every
attempt, goes green, stops early, and gets the rounding wrong the same way
three times.

Qwen3.6-27B is also the cleanest operator in the table -- spec read on 15 of
15, no malformed calls, no truncated arguments, no history compaction, no
refused edits, and a third of its step budget -- and it pays for the same score
in wall clock, at 0.55 tok/s against 1.9.

### Published benchmarks do not predict this one

Qwen3.6-35B-A3B was added to find out whether the MoE argument above could be
pushed further: 35B of knowledge for 3B of per-token memory traffic, against
the 27B's 27B dense. On throughput it wins outright, and by more than the
arithmetic promised -- **3.4 tok/s against 0.55**, six times its dense sibling
of the same generation, which is the difference between an eight-hour suite and
a twenty-hour one.

It scores **7%**.

That is one solved attempt in fifteen, from a model whose published SWE-bench
Verified (73.4%) sits within four points of the 27B's (77.2%). The two numbers
disagree because they measure different things, and the column that shows it is
`green but wrong`: **11 of 15**, near triple either leader's 4. It goes green on
80% of the suites it can run and is right on almost none of them.

The transcripts say plainly why. On `crash-recovery` it read `SPEC.md`, and at
step 8 wrote out the spec-only bug itself, unprompted:

> The current code has `if lsn < checkpoint.lsn: continue` which skips records
> with `lsn < checkpoint.lsn` but not `lsn == checkpoint.lsn`. This should be
> `lsn <= checkpoint.lsn`. Let me run the tests first...

It ran the tests, saw 13 of 13 green, and called `finish` -- never applying the
fix it had just diagnosed in writing. One edit, nine of thirty steps, every
visible test passing, every one of the seven held-out checks failing.

So the failure is not comprehension. It found the rule that nothing pointed it
towards, stated it correctly, and then let a green suite overrule it. The
held-out design exists to catch exactly that, and no model here has
demonstrated it more cleanly: this is what it looks like when a model treats
the tests it can run as the definition of done.

Its other failure mode is cruder. Three attempts ended `no_call` -- a hundred
minutes of reasoning apiece, zero edits, no tool call ever emitted. Thinking
without acting, which at 3.4 tok/s is still an hour and a half of wall clock
spent reaching nothing.

The practical lesson for picking the next model: **leaderboard position is not
the signal.** gpt-oss-20b ties the 27B here from well below it on SWE-bench,
and Qwen3.6-35B-A3B lands near the 27B on SWE-bench and an order of magnitude
below it here. What the two 73% models share is not a benchmark score but a
disposition -- they keep working after the visible gradient goes flat, spending
42% and 33% of their step budgets against the 35B-A3B's 30%.

### Why that took a rebuild to see

The same four models, on the same five tasks, scored like this when the only
suite was the one they could run:

| Model | runnable suite only | with a held-out suite |
|---|---|---|
| gpt-oss-20b-MXFP4 | 100% | 73% |
| Qwen3-Coder-30B-A3B | 67% | 0% |
| Devstral-Small-2507 | 60% | 0% |
| Qwen2.5-Coder-32B | 40% | 0% |

Nothing about the tasks changed. What changed is that the model can no longer
run the thing it is scored on. A suite a model can run to completion measures
how well it hill-climbs a gradient you handed it, and the weaker the model the
harder it leans on that -- 2.1 test runs per attempt for the strongest, 8.8 for
the weakest.

This matters because the first version of these numbers was reassuring and
wrong. It said a 20B model was perfect at agentic coding and a 30B was
competent, while the same models, in the same week, went 0 for 3 on the one
episode of the retired audit suite that had no oracle -- recording a
well-formed, verified answer to a question nobody asked, every single time.

### Reading the spec is not a preference

| | solved |
|---|---|
| opened the spec file | 23 of 41 (56%) |
| did not | **0 of 14 (0%)** |

Across all 55 attempts, nothing has ever solved a task without opening the file
that states the rule.

The cleanest case is gpt-oss on `inventory-ledger`, the same model and task
three times over:

| attempt | opened `README.md` | visible suite | solved |
|---|---|---|---|
| 0 | no | green | fail, 5 of 7 held-out failing |
| 1 | **yes** | green | **PASS** |
| 2 | no | green | fail, 5 of 7 held-out failing |

The only variable is whether it went and read the file nothing pointed it at.

### The failure modes are still unrelated

The ranking is the least interesting part; the three models that score zero
get there differently.

- **Qwen3-Coder-30B is over-confident.** Six attempts satisfied every visible
  test and failed the held-out suite; four more called `finish` on a red suite.
  It is the only model that does the latter.
- **Devstral spins.** One attempt spent 26 steps and made **zero edits**;
  another made one edit in 28 steps over five hours.
- **Qwen2.5-Coder-32B cannot use the tools or quote code.** Every one of its
  calls arrived as reply text rather than in the tool-call field, it never
  opened a spec in any attempt, and its edits are refused at ten times the rate
  of the other models'.

### Mixture-of-experts is not optional here

The dense models read 14 and 20 GB per token against the MoE pair's ~2, and
that is the whole difference between 1.9 tok/s and 0.4. Over a twenty-turn task
it compounds: gpt-oss finished fifteen attempts in 5.7 hours, Qwen2.5-Coder-32B
took 10.2 hours for five.

## Reading the results

Each run appends to `results/<label>.jsonl`, flushed after every attempt, so an
overnight run that dies at 4am keeps everything it finished. Re-running the
same label resumes where it stopped. A readable transcript of every attempt
lands in `results/transcripts/<label>/`, and those are committed.

**Read the transcripts.** A rate tells you a model failed; only the transcript
tells you whether it never opened the spec, edited a file it had not read, or
got the suite green and then broke it again on the next call. Those are
different problems with different fixes and they look identical in a score.

**solved** is the score, and it is the only column that is: the fraction of
attempts where the hidden suite passes against what the model left behind --
not what the model claimed, and not whether some intermediate run went green.
The rest explain how:

- **operates tools** -- four fifths of calls in the tool-call field, four
  fifths not refused, at least three distinct tools. A floor, not a skill:
  below it nothing else in the row means anything.
- **verifies** -- ran the tests at least once. A model that edits blind is
  guessing even when it guesses right.
- **reads the spec** -- opened the file holding the requirement that cannot be
  inferred. Nothing points it there.
- **false done** -- called `finish` with tests still failing. The agentic
  failure that costs most in real use: confident, well-formed, and wrong.

`results/archive/` holds the two suites this replaced, with their results and
their report, unchanged.

## Tool-call protocols

Tool calls go over the `tools` API parameter by default, the way a real agent
drives a model, so results transfer. `--protocol text` describes the tools in
the system prompt instead, for servers that reject the parameter; `auto` picks
by testing whether the *server* accepts it, never whether the model used it,
because a model that is offered tools and ignores them is exactly what this
suite is trying to catch.

A call written into the reply text instead of the tool-call field is salvaged
and executed, so the rest of the attempt can still be measured -- but counted
as malformed, and a model whose calls mostly arrive that way fails the
`operates tools` floor. A real agent reads the field, finds it empty, and sees
a model that said nothing at all.

**A reply carried in a reasoning channel is not silence.** A model in the
harmony format may answer entirely in its analysis channel, which llama-server
returns as `reasoning_content` beside an empty `content`. Reading only
`content` there scores the harness rather than the model -- it once recorded a
model at 0% while its discarded replies contained the correct tool calls -- so
both are read.

## Tuning

`scripts/speed-test.sh models/foo.gguf` sweeps thread counts with `llama-bench`
and reports prompt-processing and generation speed separately. On a 2-core
machine more threads is not reliably better, since hyperthreads contend for the
same memory ports — measure rather than assume. `serve.sh` defaults to physical
core count and honours `THREADS`, `CTX`, `PORT`, and `MLOCK` from the
environment.

Quantisation is the other lever. Q4_K_M is the default choice here because it
roughly halves bytes-read-per-token versus Q8 for a small quality cost; on a
bandwidth-bound box that is close to a 2x speedup. Q5_K_M is worth testing when
a model is close to passing but sloppy.

Context size matters more here than it did for single-shot prompting, and it is
easy to get wrong in both directions:

- **Too small silently destroys scores.** An agentic conversation grows with
  every file read and every test report. If it outgrows the context the model
  loses the beginning of its own investigation and starts repeating work.
  gpt-oss-20b at `CTX=8192` previously hit the ceiling mid-thought on 7 of 12
  single-shot attempts; a tool loop reaches that ceiling far sooner.
- **Too large costs real speed.** Raising the same model to `CTX=32768` dropped
  it from 5.1 to ~3.2 tok/s, because attention work grows with sequence length
  and the KV cache competes for the same scarce bandwidth.

## A note on running model-generated code

The harness executes model output in a subprocess with a wall-clock timeout, a
2 GB address-space cap, a process-count cap, and a scratch working directory
that is deleted afterwards.

Those limits stop *accidents* — runaway loops, memory bombs, a stray
`while True`. They are **not** a security boundary. The code runs as your user,
with your filesystem and your network. That is an acceptable trade for
benchmarking known-good open-weight models on this suite's prompts, but if you
ever point the harness at untrusted prompts or untrusted weights, put it in a
container or a VM first.
