# Reproduction

## Scope

This artifact supports new inference on the exact frozen inputs and offline
scoring/analysis of responses that the reader supplies. It intentionally does not
include historical answers or scored results, so it cannot by itself recreate
the authors' numerical result tables. No GPU or API call is part of validation.

Scientific modules are relocated from frozen source into functional packages.
Changes are limited to import wiring, portable paths, scientific configuration
lookup, and removal of private scheduling/credential-discovery drivers. The
portable runner is a new adapter, not a claim of byte-identical reproduction of
the original infrastructure. `docs/source_provenance.json` records source hashes.

## Environment

Install the CPU package with `python -m pip install -e .`. NumPy 1.26.4 is pinned
for numerical bootstrap reproduction. Source-only validation, export and parsing
use the standard library; statistical modules additionally require NumPy.
Use `--root` before the subcommand when running from outside the artifact directory.

For optional local inference, set up vLLM 0.18.0 in a separate GPU environment.
Stage the model checkpoint yourself at a pinned revision from
`configs/models/registry.json`. Weights and third-party dependencies are not
redistributed. Serving hardware and tensor parallelism depend on the checkpoint
and available memory; choose them explicitly for your environment.

Example for a compatible, already staged checkpoint:

```bash
vllm serve /path/to/local/checkpoint --served-model-name Qwen/Qwen3.5-9B \
  --dtype bfloat16 --max-model-len 16384 --tensor-parallel-size 1 \
  --host 127.0.0.1 --port 8000
```

The client uses the frozen open-model greedy/non-thinking generation profile.
Verify the tokenizer and chat-template identity from the registry before claiming
an exact model comparison. The portable client does not automatically certify
your server's weights, tokenizer, input length, or runtime. `backends/tokenization.py`
provides the original flat-token counting helper. Do not silently truncate inputs.

Hosted models use native provider settings: Chat Completions receives model and
messages; Responses receives model and input; Anthropic Messages receives model,
system, messages and `max_tokens=1024`. No additional temperature or reasoning
settings are silently introduced. Open and hosted decoding settings differ and
must be disclosed in comparisons. Endpoints and API keys come from environment
variables and are absent from distributed configuration.

## Full workflow

```bash
epistemic-benchmark validate --study interventions
epistemic-benchmark run --study interventions \
  --config configs/models/local.example.json --output outputs/intervention-run
epistemic-benchmark score --study interventions \
  --attempts outputs/intervention-run/attempts.jsonl --output outputs/intervention-scores.json
epistemic-benchmark analyze --study interventions \
  --scores outputs/intervention-scores.json --output outputs/intervention-analysis.json
```

Substitute `diagnostics` or `benchmark` to use another study. For a hosted run,
choose the appropriate client configuration and pass `--native-api` to `score`.
The runner requires a new output directory and stops on authentication/configuration
errors. It uses at most three attempts, never retries a format-invalid answer,
and never mixes a previous answer into another request. There is no automatic
resubmission, model download, scheduler submission or credential discovery.

For an interrupted run, retain its attempt journal. The public runner currently
does not implement resume; do not merge duplicate terminal requests or overwrite
the original record. The strict attempt validator rejects inconsistent histories.

## Dataset construction source

`data/worlds.py` and `data/quotas.py` implement symbolic construction.
`prompts/factorial.py`, `prompts/diagnostics.py` and `prompts/language.py` render
evidence; `prompts/naturalistic.py` and `prompts/padding.py` implement controlled
surface changes; `prompts/interventions.py` provides fact extraction, sham matching,
flat/ledger rendering and fixed-rule appendices. The frozen compressed inputs
are authoritative for reproduction. Rebuilding token-matched controls requires
the original checkpoint tokenizers, which are not included.
