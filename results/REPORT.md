# Local LLM benchmark

## Agentic coding

| Model                               | solved | any | operates tools | verifies | reads the spec | false done | steps | tok/s |
|-------------------------------------|--------|-----|----------------|----------|----------------|------------|-------|-------|
| gpt-oss-20b-MXFP4                   |   100% | 100% |           100% |     100% |            83% |          0 |   45% |   1.8 |
| Qwen3-Coder-30B-A3B-Instruct-Q4_K_M |    58% | 75% |           100% |     100% |            75% |          4 |   60% |   1.2 |
| Qwen2.5-Coder-32B-Instruct-Q4_K_M   |    25% | 25% |             0% |     100% |             0% |          0 |   88% |   0.3 |
| Devstral-Small-2507-Q4_K_M          |     0% |  0% |             0% |       0% |             0% |          0 |    8% |   0.9 |

### Reading these numbers

Sample: 4 task(s) x 3 attempt(s) per model.

**solved** is the score, and it is the only column that is. It is the
fraction of attempts where the hidden test suite passes against the
project the model left behind -- not what the model claimed, and not
whether some intermediate run went green. Everything else explains how.

- **any** — tasks solved by at least one attempt. The gap from *solved*
  measures consistency.
- **operates tools** — four fifths of calls in the tool-call field, four
  fifths not refused, at least three distinct tools. A floor, not a
  skill: below it, nothing else in the row means anything.
- **verifies** — ran the tests at least once. A model that edits blind
  is guessing even when it guesses right.
- **reads the spec** — on tasks with a requirement stated only in prose,
  whether it opened the file holding it. Nothing points it there.
- **false done** — called `finish` with tests still failing: it believed
  it was done and was not. The agentic failure that costs most in real
  use, and the one no amount of re-running the evidence can catch.
- **steps** — fraction of the step budget spent. Low with a high score
  is a model that knew when it was done; high with a low score is one
  that wandered until it was stopped.

**gpt-oss-20b-MXFP4** (native tool calls) -- 1 attempt(s) ended on a server error; 20 call(s) repeated a call already made; 1 edit(s) were refused; 3.3 edits and 2.2 test runs per attempt
**Qwen3-Coder-30B-A3B-Instruct-Q4_K_M** (native tool calls) -- **4 attempt(s) declared done with tests failing**; 70 call(s) repeated a call already made; 13 history compaction(s) -- conversations outgrew the window and older results were summarised; 4.7 edits and 6.2 test runs per attempt; never solved: route-matcher
**Qwen2.5-Coder-32B-Instruct-Q4_K_M** (native tool calls) -- 100% of calls were malformed or named no tool (75 written in the reply text); 1 attempt(s) ended on a server error; 35 call(s) repeated a call already made; 17 edit(s) were refused; 1 history compaction(s) -- conversations outgrew the window and older results were summarised; 4.2 edits and 5.2 test runs per attempt; never solved: inventory-ledger, retry-policy, route-matcher
**Devstral-Small-2507-Q4_K_M** (native tool calls) -- 4 attempt(s) ended with prose instead of a call; 0.0 edits and 0.0 test runs per attempt; never solved: inventory-ledger, log-compactor, retry-policy, route-matcher
