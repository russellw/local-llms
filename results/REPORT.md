# Local LLM coding benchmark

| Model                               | pass@1 | pass@any | tok/s | runtime | algorithm | bugfix | datastruct | spec |
|-------------------------------------|--------|----------|-------|---------|-----------|--------|------------|------|
| gpt-oss-20b-MXFP4                   | 81%    | 83%      | 5.1   | 597m    | 100%      | 100%   | 100%       | 42%  |
| Qwen3-Coder-30B-A3B-Instruct-Q4_K_M | 58%    | 58%      | 5.9   | 46m     | 75%       | 100%   | 100%       | 0%   |
| qwen2.5-coder-7b-instruct-q4_k_m    | 33%    | 42%      | 3.2   | 57m     | 33%       | 83%    | 50%        | 0%   |
| qwen2.5-coder-1.5b-instruct-q4_k_m  | 8%     | 8%       | 13.4  | 14m     | 0%        | 50%    | 0%         | 0%   |

**gpt-oss-20b-MXFP4** -- 7 attempt(s) never finished generating within the request timeout -- too slow rather than wrong; never solved: csv-parser, expression-eval
**Qwen3-Coder-30B-A3B-Instruct-Q4_K_M** -- never solved: csv-parser, event-emitter, expression-eval, merge-intervals, semver-compare
**qwen2.5-coder-7b-instruct-q4_k_m** -- 1 solution(s) hung when executed; never solved: autocomplete-trie, binary-search-insert, csv-parser, event-emitter, expression-eval, merge-intervals, semver-compare
**qwen2.5-coder-1.5b-instruct-q4_k_m** -- never solved: autocomplete-trie, binary-search-insert, csv-parser, event-emitter, expression-eval, fix-min-heap, merge-intervals, rle-codec, roman-numerals, semver-compare, topological-sort
