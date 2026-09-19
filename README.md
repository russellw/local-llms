# local-llms

[![selfcheck](https://github.com/russellw/local-llms/actions/workflows/selfcheck.yml/badge.svg)](https://github.com/russellw/local-llms/actions/workflows/selfcheck.yml)

Benchmarking locally-runnable LLMs on ordinary CPU hardware.

Every model here runs on the machine in front of you: no GPU, no API key, no
data leaving the box.

There are **two suites**, because there are two different ways a local model
turns out to be unusable and one of them is invisible to the other:

| suite | asks | scored by |
|---|---|---|
| **code** | can it write a correct function from a precise spec? | hidden unit tests |
| **tool-loop** | can it operate an agent loop — choose tools, recover from a refusal, go and find what it was not handed, and stop? | re-running the query a finding carries |

They are never averaged. A 7B can score respectably on the first and record
nothing at all on the second, and a number that splits the difference would
describe neither. The tok/s figures sit alongside both, because on this
hardware **too slow to use** is a third way to be unusable.

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

## Quick start

```bash
scripts/build.sh                     # build llama.cpp (slow: ~15 min on 2 cores)
scripts/fetch-model.sh Qwen/Qwen2.5-Coder-7B-Instruct-GGUF \
    qwen2.5-coder-7b-instruct-q4_k_m.gguf

scripts/serve.sh models/qwen2.5-coder-7b-instruct-q4_k_m.gguf   # terminal 1
python3 -m bench toolloop --label qwen2.5-coder-7b-q4           # terminal 2, ~5 min
python3 -m bench run      --label qwen2.5-coder-7b-q4           # terminal 2, ~1 hour
```

Run the tool-loop suite first. It is two orders of magnitude cheaper — a few
hundred tokens an episode against a few thousand a coding task — and a model
that cannot drive a loop will tell you so in the first five minutes, before you
spend an hour finding out it writes lovely Python.

No `pip install`: the harness is standard library only, so it runs on a bare
Python 3.11+.

## Commands

| Command | What it does |
|---|---|
| `python3 -m bench tasks` | list both suites |
| `python3 -m bench selfcheck` | validate the tasks, the harness and the tool-loop scorer |
| `python3 -m bench run --label NAME` | run the code suite against the served model |
| `python3 -m bench toolloop --label NAME` | run the tool-loop suite against the served model |
| `python3 -m bench report --write` | regenerate `results/REPORT.md` from all runs |

Useful `run` flags: `--task <id-or-category>` (repeatable) to run a subset,
`--repeats N` to sample each task N times, `--fresh` to discard prior results.
`toolloop` takes the same, with `--episode` in place of `--task`.

Runs default to temperature 0. That is the right setting for a single pass —
greedy decoding is deterministic, so the score is reproducible. It is the wrong
setting for `--repeats > 1`, where every attempt would return the identical
answer, so passing repeats without a temperature switches to 0.2 and says so.

**`selfcheck` is the guard rail.** A benchmark whose tests are subtly wrong
measures nothing, so it checks three things:

- every task's `reference.py` passes its own `tests.py`
- the harness itself behaves — code extraction handles the dozen ways a model
  can wrap (or fail to wrap) a code block, and the sandbox actually fails wrong
  answers, fails syntax errors, kills infinite loops, and isolates workdirs
- the tool-loop scorer behaves. That suite has no reference solution to
  execute, so its guard is a set of scripted agents played against the scorer:
  a correct one must score every axis, a *plausible-looking wrong* one must be
  caught, a spiralling one must score zero, and one that writes prose instead
  of calling anything must not be credited with operating the tools.

Run it after touching any task. It has already caught three bugs — two in
tests, one in a reference — that would otherwise have been silently scored
against the models.

## Suite one: the coding tasks

Twelve tasks, all verified by executing the model's code against hidden unit
tests. Nothing is graded by eyeballing or by another model.

| Category | Tasks | What it probes |
|---|---|---|
| `algorithm` | rle-codec, merge-intervals, roman-numerals, binary-search-insert | baseline competence and edge cases |
| `datastruct` | topological-sort, autocomplete-trie | does it build the structure that was asked for |
| `bugfix` | fix-lru-cache, fix-min-heap | reading broken code and reasoning about *why* it is broken |
| `spec` | event-emitter, csv-parser, expression-eval, semver-compare | following a long, precise specification exactly |

The suite is deliberately weighted away from "recite a LeetCode answer".
Several tasks defend against the shortcut rather than the wrong answer:

- **binary-search-insert** passes the sequence in as an object that counts
  index accesses and refuses to be iterated, so a linear scan fails outright.
- **autocomplete-trie** checks that a rare prefix in a 20,000-word dictionary
  stays cheap, so a flat list with `startswith` fails.
- **csv-parser** and **expression-eval** forbid the stdlib module that would
  trivialise them.
- **fix-lru-cache** and **fix-min-heap** hand the model plausible-looking code
  with several interacting bugs, which is much closer to real work than writing
  from scratch.

`spec` is usually the category that separates models. Small models can often
produce a working algorithm but lose points on the sixth clause of a
specification — precisely the failure mode that makes a coding assistant
frustrating in practice.

### What the coding tasks do not measure

Stated plainly, because these are deliberate boundaries rather than oversights:

**Training-data contamination is not eliminated, only made less useful.** An
LRU cache, a min-heap, a CSV parser and a semver comparator are all classic
exercises that are certainly in every model's training data. That is survivable
because the tasks do not score "did you recognise this problem" — they score
conformance to a specific written spec, and the specs deliberately deviate from
the textbook version. `merge-intervals` merges intervals that are merely
*adjacent*, not just overlapping. `rle-codec` writes the count even when it is 1.
The observed failures match this design: models produce the recognisable general
shape and then miss a clause. A model that had memorised the answer outright
would not fail that way. Treat contamination as damped, not absent.

**Sample size is small.** Twelve tasks resolves large differences between
models and nothing finer. `results/REPORT.md` restates this next to the numbers.

**Scope is single-file Python.** Every task is one self-contained module with a
clean specification. Real coding work is multi-file, involves existing code you
did not write, and is iterative — you get a failing test and try again. None of
that is measured here. A model that scores well on this suite has demonstrated
that it can write correct Python to a precise spec; it has not demonstrated that
it can work in your codebase.

**Nothing here is agentic.** One message in, one message out, no tools, no
state, no second chance. That is the single biggest blind spot in this suite
and it is why the second one exists.

**One hardware configuration, one quantisation.** Results are Q4_K_M (or the
model's native format) on one CPU. Quantisation quality effects and any
GPU-relevant conclusions are out of scope; the tok/s figures transfer to nothing
but a machine with similar memory bandwidth.

### Adding a task

Create `tasks/<id>/` with three files, and an entry in `tasks/manifest.json`:

- `prompt.md` — the user message. Be exhaustive about edge cases; ambiguity in
  the prompt shows up as noise in the scores.
- `tests.py` — imports from `solution`, prints failures, exits non-zero. Report
  *all* failures rather than stopping at the first: the detail is what makes a
  result diagnosable later.
- `reference.py` — a known-good solution. Then run `python3 -m bench selfcheck`.

## Suite two: the tool loop

### Why a second suite

The scores above are real and they are also misleading, in a specific way that
took an unrelated project to notice.

A separate piece of work drove five models through an agentic data audit: pick
among tools, investigate a dataset you can only see through them, and record
findings whose evidence gets re-executed before it is kept. The models that
score respectably on the coding tasks above were, in that loop, **inert**. One
30B-class model made forty tool calls across three runs, every single one of
them the same tool, and recorded nothing. A 4B in the same harness recorded
real findings. The ordering was not merely weaker than the coding scores
predicted — in the middle of the table it was *inverted*.

The lesson is not that the coding suite is wrong. It measures what it says it
measures, and small models really are decent at writing a specified function,
because that is the densest thing in their training data. The lesson is that
**coding ability and loop-driving ability are separate axes that fail in a
different order**, and a benchmark that only reports the first will keep
telling you a model is usable right up until you put it in an agent.

That comparison ended up separating the tiers on four things, none of which was
knowledge or code quality:

| | operates the tools | not confused by shapes | asks the right question | seeks out information |
|---|---|---|---|---|
| small local models | 1 of 3 | no | — | no |
| a 63 GB local model | yes | yes | **no** | **no** |
| a frontier model | yes | yes | yes | yes |

This suite is those four columns, made cheap enough to run on a laptop.

### The episodes

Four episodes against a tiny fixed dataset — a metering export joined to a
premises register, with defects planted in it. There is no database and no
network: `bench/toolloop/world.py` is the whole thing, and `selfcheck`
re-derives every number the episodes expect, so a careless edit fails CI
instead of quietly changing the question.

| Episode | Probes | The trap |
|---|---|---|
| `basics` | mechanics | nothing. Count the negative values in a column, record it, stop. A model that cannot do this cannot do any of the rest. |
| `shapes` | recovery | the column can only be *sampled*, and sampling returns `99 Aaaaaaa Aaaaaa` — a shape, not a value. A model that searches for the shape is refused and has to work out why. |
| `dictionary` | initiative | the question is "how many states are not valid", and which states are valid is written only in a customer document nobody told it to open. |
| `premise` | judgment | the join works literally and gives **14**. The answer is **4**, and the reason — that both sides carry a decorative prefix — is in the same unopened document. |

`premise` is the one worth watching, because it is the failure that survives
every safeguard. The model writes a well-formed query, the harness re-runs it,
the number matches what the model claimed, and the finding is recorded. It is
correct, verified, and answers a question nobody asked. Evidence re-execution
catches an invented number; it cannot catch a well-formed question about the
wrong premise, and no amount of tightening the harness will change that.

A 1.5B model reached that failure on its first attempt, in three steps and
twenty-four seconds.

### How it is scored

**Only queries are scored. Prose is never scored.** A finding counts when the
tool call it carries is about the right column and returns the right number —
both machine-readable. Titles, summaries and explanations are written to the
transcript for a human to read and contribute nothing. A benchmark that grades
text has to decide what a good sentence is, and this one declines to.

The report gives four rates and no total:

- **operates tools** — four fifths of its calls arrived in the tool-call field
  rather than the reply text, four fifths came back with an answer rather than
  a refusal, and it reached for at least three different tools. A floor, not
  a skill.
- **not confused by shapes** — of the attempts that were refused for searching
  on a redaction, the fraction that then did something different. Blank means
  the trap was never sprung.
- **asks the right question** — the fraction of episodes where the defect was
  actually established. This is the score.
- **seeks out information** — of the episodes whose answer is only in a
  supplied document, the fraction where any document was opened.

Plus the diagnostics that turned out to matter more than the rates: how much of
the step budget was spent, whether the run ended because the model decided it
had or because the budget stopped it, how many calls repeated a call already
made, and how many findings were rejected for claiming a number their own
evidence did not return.

**Tool calls go over the `tools` API parameter by default**, the way a real
agent drives a model, so results transfer. `--protocol text` describes the
tools in the system prompt instead, for servers that reject the parameter;
`auto` picks by testing whether the *server* accepts it, never whether the
model used it, because a model that is offered tools and ignores them is
exactly what this suite is trying to catch.

A call written into the reply text instead of the tool-call field is salvaged
and executed, so the rest of the episode can still be measured — but counted as
malformed, and a model whose calls mostly arrive that way fails the
`operates tools` floor. That is not a technicality. qwen2.5-coder-1.5b emits
the right tool name and every argument correctly, and then wraps the object in
a markdown fence instead of the `<tool_call>` tags its own chat template
explicitly asked for, on **every call it makes**. Verified against the template
the server reports, so this is the model missing an instruction it was given,
not the plumbing failing to offer one. A real agent reads the field, finds it
empty, and sees a model that said nothing at all.

When a model fails the floor purely on channel, re-run it with
`--protocol text`, which asks for the same calls as a JSON block and so scores
what it was actually doing. The pair separates *cannot follow the tool-call
protocol* from *cannot reason in a loop* — two different problems, and only the
first one has a workaround.

**Read such a pair as a diagnostic, not a ranking.** The two protocols are not
equivalent measurements: the text one spends several hundred tokens of system
prompt describing the tools, which is itself a burden on a small model. On the
1.5B the two rows disagree in both directions — the channel fix takes
`operates tools` from 0% to 42%, and the score it was actually after *falls*.
Fixing the plumbing did not make it able to do the job, which is the more
useful thing to learn.

### What the tool loop does not measure

**It is not a measure of judgment in general.** Four episodes on one small
fixture. A model that passes `premise` has read one document and applied one
rule; it has not demonstrated that it would audit your data well.

**The dataset is fixed and in the open.** Nothing stops a future model from
having read this repository. The episodes are cheap to replace and the numbers
are all derived in `world.py`, so swapping the fixture is a small job — but
today the defence is that the file is obscure, which is not much of one.

**Passing the floor says little.** `operates tools` at 100% means the model can
hold a fork. Everything interesting is in the last two columns.

**No ceiling has been established.** `selfcheck` proves each episode is
*mechanically* solvable — a scripted agent making the right calls scores it —
but that is a weaker claim than "a competent model would solve it". Until a
model known to be capable has run this suite and scored well, a 0% could in
principle be an episode's fault rather than a model's. Treat a low score as a
reason to open the transcript, which is what the transcripts are for.

### Adding an episode

Episodes live in `bench/toolloop/episodes.py` — a brief, a step budget, and a
`Target` naming the columns the evidence must reference and the number it must
return. Plant the defect in `world.py`, add its expected count to
`_world_checks` in `bench/toolloop/selftest.py`, and add a scripted ideal agent
to `_IDEAL` there. `selfcheck` then holds you to it: if your ideal agent cannot
score the episode, models have no chance either, and you will find out in
seconds rather than after an overnight run.

## Reading the results

Each run appends to `results/<label>.jsonl`, flushed after every task, so an
overnight run that dies at 4am keeps everything it finished. Re-running the
same label resumes where it stopped. Full model responses land in
`results/responses/<label>/` (gitignored) — read those when a score surprises
you.

Tool-loop runs work the same way one directory down, in `results/toolloop/`,
with a readable transcript of every episode in
`results/toolloop/transcripts/<label>/`. **Read the transcripts.** The rates
tell you a model missed; only the transcript tells you it named a table that
does not exist, was handed the list of real tables in the error, and quit —
which is a different problem from not knowing the answer, and the two look
identical in a score.

The code report shows:

- **pass@1** — mean success rate over all attempts. The headline number.
- **pass@any** — solved at least once. With `--repeats > 1` the gap between
  these two measures consistency, which matters more than peak ability when
  you are waiting minutes per answer.
- **tok/s** — median generation speed, taken from llama.cpp's own timings.
- Notes separating the failure modes that are *not* "wrote wrong code":
  responses that hit the token limit, responses containing no code block, and
  attempts that never finished generating inside the request timeout. That last
  one means **too slow to use**, not **too stupid to solve** — a distinction
  worth keeping, since on this hardware a reasoning model can spend over an
  hour on a single task and be marked wrong for it.

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

Context size is a lever in both directions, and it is easy to get wrong:

- **Too small silently destroys scores.** Context must hold the prompt *and*
  the entire response. gpt-oss-20b at `CTX=8192` hit the ceiling mid-thought on
  7 of 12 `spec` attempts and returned no code at all — scoring zero on ability
  it may well have had. If a model shows truncated responses in the report,
  raise `CTX` before believing the number.
- **Too large costs real speed.** Raising the same model to `CTX=32768` dropped
  it from 5.1 to ~3.2 tok/s, because attention work grows with sequence length
  and the KV cache competes for the same scarce bandwidth. Provision context
  for the responses you actually see, not for the maximum the model supports.

## A note on running model-generated code

`bench/sandbox.py` executes model output in a subprocess with a wall-clock
timeout, a 2 GB address-space cap, a process-count cap, and a scratch working
directory that is deleted afterwards.

Those limits stop *accidents* — runaway loops, memory bombs, a stray
`while True`. They are **not** a security boundary. The code runs as your user,
with your filesystem and your network. That is an acceptable trade for
benchmarking known-good open-weight models on this suite's prompts, but if you
ever point the harness at untrusted prompts or untrusted weights, put it in a
container or a VM first.
