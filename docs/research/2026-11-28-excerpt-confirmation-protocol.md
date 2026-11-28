# Excerpt alignment confirmation protocol

Freeze this protocol, corpus and scorer before running any arm. Use the
unchanged Rust probe from `54045c7b63189928bb2698eb8398691e55198115`.
Compare its original normalized, identifier-aligned, and code-weighted
arms with the same file ranking, byte and file limits.

Six authored lineages contribute 24 source-only cases and 28 required
spans. The cases comprise eight long implementation queries, eight
documentation-dependent queries, four mixed-evidence queries and four
short-file controls. Mixed cases require both code and documentation.
One case deliberately requires two regions in the same file that
cannot both fit in its single excerpt. Eleven of the remaining
documentation and mixed spans are distributed among separate fixtures.
The development cases and earlier 56-task confirmation are excluded.

Each probe receives only the disposable repository root, the prompt,
and strategy flags. The scorer keeps annotations outside the root and
requires the full inclusive line interval for each span. It checks the
reported byte count against the unchanged source interval, the four-file
and 12 KiB/file limits, visible incompleteness on truncated results,
ordered path and complete-file parity, deterministic delivery, and
unchanged source inventories. Missing files or spans receive no credit.

Rotate arm order across three process starts per case and measure
three in-process calls each time. Report median and nearest-rank p95 of
per-case latency medians, maximum process working-set high-water mark
where available, total delivered bytes, and number of truncated
excerpts. Timing excludes subprocess launch. Report complete tasks by
family and documentation span recall across both documentation and
mixed tasks, with task-level evidence preserved.

For a candidate to meet the proposed lab gate, require at least 90%
overall required-span recall, strictly better complete-task evidence
recall than baseline, and every documentation span the baseline
delivered. Require all four short controls to pass under baseline and
candidate with unchanged complete-file results, zero observed scope,
completeness or budget violations, and no more than 20% median latency
overhead. A failed gate is a research result. Keep the strategies and
corpus fixed through the report. Success on this small synthetic
confirmation provides no production qualification.
