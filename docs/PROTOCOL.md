# Measurement protocol

## Benchmark tracks

T1 measures initial-state representation, source/provenance understanding and
relative reliability, with exact counts as secondary probes. T2 measures the
complete 2×2×2 quality/reliability/independence factorial. T3 swaps source
reliability. T4 separates text order, event time, repetition, speakers and
independent evidence. T5 tests explicitly verified states. Each model receives
48 requests per world, or 24,000 in total.

## Intervention conditions

| ID | Condition | Purpose |
|---|---|---|
| C0 | Original baseline | Same-batch baseline measurement |
| C1 | Matched sham appendix | Extra text/layout control |
| C2 | Flat factual appendix | Re-presentation of relevant facts |
| C3 | Structured ledger | Same factual content organized by source/evidence |
| C4 | Ledger plus fixed rule | Explicit instruction about evidence weighting |

There are 20 independent tasks per world per condition: eight factorial decisions,
two reliability swaps, four text/time decisions, four report-structure decisions
and two verified decisions. The total is 50,000 requests per model. C2 and C3 use
the same fact set; C4 adds the same fixed rule to the unchanged C3 ledger. No
answer, ranking of the final alternatives, or verified truth is added to the
appendix. Baselines are rerun when collecting a new intervention experiment.

The declared primary family has 48 comparisons: three models × two main subsets
× four comparisons × two endpoints. Per-model analysis preserves the family
specification; use `scripts/collect_intervention.py` to apply Holm across the
complete predeclared three-model set. Do not silently shrink the family after
missing runs or select models based on their effects.

## Parsing, missingness and statistics

The integer protocol accepts exactly one integer from 0 through 8. Choice tasks
accept only a JSON object with the single legal `answer` option. The frozen
parser also permits one JSON code fence. Invalid formatting is recorded, never
repaired by another generation. Retries are limited to technical failures.

Truth-bearing task accuracies and unverified choice effects have distinct
denominators. Preserve technical failures, protocol deviations, truncated outputs
and invalid formats. Unverified missing choices must not be imputed as state A.
Report usable-world counts and worst-case bounds. Whole-world bootstrap keeps
factorial conditions and paired interventions together. Absolute effects are
computed as the absolute mean, recomputed within each shared bootstrap sample;
they are not averages of per-world absolute values.

The intervention and benchmark routines use 5,000 bootstrap draws and seed
20261001. Diagnostic routines use 2,000 draws and seed 20260929. The exact designs
and contrast definitions are in `configs/` and `src/epistemic_benchmark/analysis/`.
Zero empirical errors or degenerate intervals do not establish population-zero
error. Correct independent probes do not demonstrate same-forward-pass knowledge.
