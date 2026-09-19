# Local LLM benchmark

## Writing code

| Model                               | pass@1 | pass@any | tok/s | runtime | algorithm | bugfix | datastruct | spec |
|-------------------------------------|--------|----------|-------|---------|-----------|--------|------------|------|
| gpt-oss-20b-MXFP4                   | 81%    | 83%      | 5.1   | 597m    | 100%      | 100%   | 100%       | 42%  |
| Qwen3-Coder-30B-A3B-Instruct-Q4_K_M | 58%    | 58%      | 5.9   | 46m     | 75%       | 100%   | 100%       | 0%   |
| qwen2.5-coder-7b-instruct-q4_k_m    | 33%    | 42%      | 3.2   | 57m     | 33%       | 83%    | 50%        | 0%   |
| qwen2.5-coder-1.5b-instruct-q4_k_m  | 8%     | 8%       | 13.4  | 14m     | 0%        | 50%    | 0%         | 0%   |

### Reading these numbers

Sample size: 12 tasks x 3 attempt(s) per model (36 attempts per model).

That is small, and the honest reading follows from it. The coarse ordering is
robust — the gap between the best and worst model here is far larger than the
noise. **Adjacent gaps are not.** Repeated attempts at the same task are
correlated, so the effective sample size is closer to the number of *tasks*
than the number of attempts; a few points between neighbouring models is a tie,
not a ranking.

Column meanings:

- **pass@1** — mean success rate across all attempts.
- **pass@any** — fraction of tasks solved by at least one attempt. The gap
  between this and pass@1 measures consistency.
- **tok/s** — median generation speed, from llama.cpp's own timings.
- **runtime** — total wall clock spent generating, across all attempts.

Per-category percentages come from even fewer tasks each (two to four), so read
them as a direction to investigate rather than a measurement.

**gpt-oss-20b-MXFP4** -- 7 attempt(s) never finished generating within the request timeout -- too slow rather than wrong; never solved: csv-parser, expression-eval
**Qwen3-Coder-30B-A3B-Instruct-Q4_K_M** -- never solved: csv-parser, event-emitter, expression-eval, merge-intervals, semver-compare
**qwen2.5-coder-7b-instruct-q4_k_m** -- 1 solution(s) hung when executed; never solved: autocomplete-trie, binary-search-insert, csv-parser, event-emitter, expression-eval, merge-intervals, semver-compare
**qwen2.5-coder-1.5b-instruct-q4_k_m** -- never solved: autocomplete-trie, binary-search-insert, csv-parser, event-emitter, expression-eval, fix-min-heap, merge-intervals, rle-codec, roman-numerals, semver-compare, topological-sort

## Operating an agent loop

| Model                               | operates tools | not confused by shapes | asks the right question | seeks out information | steps |
|-------------------------------------|----------------|------------------------|-------------------------|-----------------------|-------|
| qwen2.5-coder-1.5b-instruct-q4_k_m  | 0%             | -                      | 25%                     | 0%                    | 35%   |
| qwen2.5-coder-1.5b-q4_k_m-textproto | 42%            | 67%                    | 8%                      | 0%                    | 50%   |

### Reading these numbers

Sample: 4 episodes x 3 attempt(s) per model.

These are four separate questions, not one score, and they are ordered the way
a model fails them. A model that cannot work the tools never gets far enough to
ask a wrong question; a model that asks the right question without being
pushed to the information is doing something the first three columns cannot
show.

- **operates tools** — four fifths of its calls arrived in the tool-call field
  rather than the reply text, four fifths came back with an answer rather than
  a refusal, and it reached for at least three different tools. A floor, not a
  skill: a model below it is unusable in a loop regardless of anything else.
- **not confused by shapes** — of the attempts where a sampled *shape* was used
  as if it were a value and refused, the fraction that then did something
  different and got an answer. Blank means the trap was never sprung, which is
  a pass by a different route.
- **asks the right question** — the fraction of episodes where the defect was
  established: a recorded finding whose re-run query is about the right column
  and returns the right number. This is the score.
- **seeks out information** — of the episodes whose answer is only in a
  supplied document, the fraction where any document was opened.

`steps` is the fraction of the step budget spent. Low with a high score is a
model that knew when it was done; high with a low score is one that wandered
until it was stopped.

**qwen2.5-coder-1.5b-instruct-q4_k_m** (native tool calls) -- **1 attempt(s) recorded the wrong-premise answer** -- a verified finding that answers a question nobody asked; re-running the evidence cannot catch this; 100% of calls were malformed or named no tool (39 written in the reply text rather than as a tool call); 8 call(s) repeated a call already made; 10 finding(s) rejected for claiming a number their own evidence did not return; 92% of episodes ended voluntarily; 2.5 distinct tools per episode; never solved: basics, dictionary, premise
**qwen2.5-coder-1.5b-q4_k_m-textproto** (text tool calls) -- 1 episode(s) hit the shape guard and never adapted; 11% of calls were malformed or named no tool (6 written in the reply text rather than as a tool call); 37% of calls were refused by a tool; 14 call(s) repeated a call already made; 1 finding(s) rejected for claiming a number their own evidence did not return; 83% of episodes ended voluntarily; 3.6 distinct tools per episode; never solved: dictionary, premise, shapes
