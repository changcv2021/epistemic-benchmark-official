# Dataset card

## Composition and intended use

The frozen set has 500 fictional worlds: 300 controlled, 120 structural and 80
naturalistic. The same worlds appear across conditions and studies. The unit of
statistical resampling is a whole world, keeping its conditions together.
These subsets measure different generalization properties; they are not a random
train/test split. No training split is provided. Development examples in source
code are distinct from the released 500-world bank.

Materials are synthetic. The naturalistic subset consists of assistant-controlled
narrative revisions reviewed for this study. It is not independently human-written
naturalistic data, and independent second-person review is not attested.
Fictional person names inside the stimuli are task content, not author identities.

## Files and fields

All `.jsonl.gz` files are UTF-8 JSON Lines compressed with gzip. Files can be read
incrementally using the standard library. Each `requests` row has a stable
`request_id` and exactly two messages: `system`, then `user`.

`worlds` stores symbolic entities, candidate states, relation family, subset,
evidence graph and renderer identity. `cases` contains rendered evidence and its
symbolic structure. `manifests` records task/probe IDs, world membership, condition,
output protocol, option mappings and input hashes. `labels` supplies the mapping
from option letters to semantic answers and `has_gold`/`gold_answer`.
Join files using `request_id`; do not infer correctness from answer position.

The diagnostic `reuse` file defines exact-input reuse relationships for verified
probes. It contains no cached model response. Intervention `baselines` records the
source case and request for each branch. `sham_matching` and `render_validation`
contain input-construction checks, not behavioral model results.

## Task semantics

Representation and explicitly verified tasks have objective answers.
Unverified conflicting-evidence decisions measure preferences and sensitivity to
controlled manipulations. They do not have a unique gold belief. Reliability
probes distinguish exact historical counts from relative reliability judgments.
Every probe is an independent context branch; its answer is never appended to a
later decision prompt.

## Limits

Benchmark reliability/time/report-count controls and intervention tasks T2–T4
use a fixed two-root diagnostic overlay on all worlds. They do not preserve every
world's original source-count topology. Benchmark core representation/factorial/
verification tasks and intervention T1/T5 preserve the original relevant graphs.
Naturalized text remains controlled synthetic prose. The evidence supports
behavioral availability and utilization comparisons, not a claim about the
knowledge present inside another forward pass.

## Versioning and provenance

`data/manifest.json` gives compressed and uncompressed SHA-256 values. Compression
does not alter the scientific JSONL bytes. Preserve frozen inputs when comparing
conditions; treat any modification as a new dataset version. Model output data
are intentionally excluded. The dataset license is pending author selection.
