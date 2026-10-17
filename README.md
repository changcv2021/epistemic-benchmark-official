#What Counts as Evidence? Epistemic Cue Utilization in Large Language Models

# Evidence Integration Benchmark

<a href="https://arxiv.org/abs/2610.12788">
  <img src="https://img.shields.io/badge/READ%20PAPER-arXiv%202610.12788-DC2626?style=for-the-badge&amp;labelColor=991B1B" height="38" alt="Read Paper">
</a>

Anonymous research artifact for measuring how language models respond to evidence
quality, source reliability, source dependence, report multiplicity, event time,
and presentation order. The intervention study compares matched prompt appendices.
This is evaluation of fixed models, with no fine-tuning or reinforcement learning.

The package contains **data and code only**. Model answers, scored outputs,
experimental result tables, model weights, credentials, and execution logs are
not distributed. Dataset labels are ground truth for the tasks that have it;
unverified belief choices deliberately have no objective gold label.

## Dataset

All studies share **500 synthetic worlds**:

| Subset | Worlds | Purpose |
|---|---:|---|
| Controlled core | 300 | Controlled mechanism contrasts |
| Structural generalization | 120 | Evidence graphs, dependence, source counts and roles |
| Naturalistic | 80 | Varied narrative surface forms |

| Study | Requests per model | Contents |
|---|---:|---|
| `benchmark` | 24,000 | Representation, factorial effects, reliability, competing cues, verification |
| `diagnostics` | 41,020 | Factorial, mechanism and verified-probe diagnostic panels |
| `interventions` | 50,000 | Baseline, sham, flat facts, ledger, ledger plus fixed rule |

These are related request inventories, not independent datasets; they contain
overlapping inputs. Do not add the counts as a measure of independent sample size.

## Layout

```text
configs/                   Scientific designs, model identities and example clients
data/
  worlds.jsonl.gz          Shared frozen world bank
  splits/                 Explicit subset membership
  benchmark/              Frozen inputs, cases, manifests and labels
  diagnostics/            Extended diagnostic inputs and reuse definitions
  interventions/          Five conditions, source baselines and matching metadata
src/epistemic_benchmark/
  data/                   Symbolic world construction and quota allocation
  prompts/                Evidence rendering, controls and intervention appendices
  backends/               Portable API client and tokenization helpers
  evaluation/             Strict parsing, attempt validation and scoring
  analysis/               World bootstrap, contrasts and grouped prediction
  utils/                  Serialization, paths and fixed study constants
tests/                    Synthetic software tests; no recorded model responses
scripts/                  Dataset checks and reproduction examples
docs/                     Dataset card, protocol and reproducibility notes
```

## Quick start

Use Python 3.11 or 3.12. Run substantial preparation and analysis on a workstation
or an allocated compute node, following the rules of your computing environment.

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
epistemic-benchmark validate --study benchmark
epistemic-benchmark validate --study diagnostics
epistemic-benchmark validate --study interventions
```

An installation is optional: use `PYTHONPATH=src python -m epistemic_benchmark`
instead of `epistemic-benchmark`. From another directory, specify
`epistemic-benchmark --root /path/to/artifact ...` or set `EPI_ROOT`.
The source package is not a separate distribution of the dataset; keep the
artifact directory and point the command at it when using a non-editable install.

Export exact independent model requests:

```bash
epistemic-benchmark export --study benchmark --output outputs/benchmark.jsonl
```

Each row contains only `request_id` and the original system/user messages.
Manifests and answer labels are never sent to the model. The compressed scientific
data retain the original uncompressed bytes; see `data/manifest.json` for checksums.

## Run your own evaluation

For an already running compatible local server:

```bash
export EPI_API_BASE=http://127.0.0.1:8000/v1
epistemic-benchmark run --study benchmark \
  --config configs/models/local.example.json --limit 2 --output outputs/smoke
```

The limit is an interface smoke test. Omit it and choose a new output directory
for a full experiment. Serving and inference consume compute or API credits.
No model is downloaded and no job is submitted by importing this package.

Use the `chat`, `responses`, or `messages` example for your own hosted deployment.
Set `EPI_API_BASE` and `EPI_API_KEY` in your environment; never commit credentials.
See [reproduction](docs/REPRODUCIBILITY.md) for provider settings and local serving.

```bash
epistemic-benchmark score --study benchmark \
  --attempts outputs/my-run/attempts.jsonl --output outputs/my-scores.json
epistemic-benchmark analyze --study benchmark \
  --scores outputs/my-scores.json --output outputs/my-analysis.json
```

Add `--native-api` when scoring provider-native hosted runs. All planned requests
remain in the scoring denominator, including missing or invalid responses.
Unverified choice effects are not accuracy scores. Bootstrap units are worlds.
There is no aggregate leaderboard score. Analysis of the full diagnostic suite
can take substantial CPU time.

Read the [dataset card](docs/DATASET_CARD.md), [measurement protocol](docs/PROTOCOL.md),
and [anonymization scope](docs/ANONYMITY.md) before interpreting results.

## Release status

This is an anonymous preparation artifact. Licensing is pending selection;
see `LICENSE_PENDING.txt`. No paper title, author list, institutional endpoint,
personal contact information, or remote repository is embedded in the package.
