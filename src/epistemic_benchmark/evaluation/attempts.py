from collections import defaultdict
from epistemic_benchmark.utils.io import digest, require

def validate_attempts(rows, selected):
    history = defaultdict(list)
    for row in rows:
        rid = row["request_id"]
        require(rid in selected, "Attempt not in run plan")
        require(row["input_hash"] == digest(selected[rid]["messages"]), "Attempt input changed")
        prior = history[rid]
        require(not prior or not prior[-1]["terminal"], "Attempt after terminal result")
        require(row["attempt"] == len(prior) + 1, "Attempt numbers must be contiguous")
        require(row["status"] in {"completed", "technical_error"}, "Unknown attempt status")
        require(row["status"] != "completed" or row["terminal"], "Completed generation must be terminal")
        require(row["attempt"] <= 3, "Retry limit exceeded")
        history[rid].append(row)
    return history
