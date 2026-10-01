#!/usr/bin/env bash
set -euo pipefail
epistemic-benchmark validate --study benchmark
epistemic-benchmark validate --study diagnostics
epistemic-benchmark validate --study interventions
