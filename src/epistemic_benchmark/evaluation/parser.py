import json
import re
from epistemic_benchmark.utils.io import require

def parse_answer(content, legal_choices, policy="strip_whitespace_or_one_json_code_fence"):
    require(policy in {"strip_whitespace_only", "strip_whitespace_or_one_json_code_fence"}, "Unknown parser policy")
    def no_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_key")
            result[key] = value
        return result

    if not isinstance(content, str) or not content.strip():
        return None, "no_answer"
    content = content.strip()
    if policy == "strip_whitespace_or_one_json_code_fence":
        fence = re.fullmatch(r'```json[ \t]*\r?\n(.*?)\r?\n```', content, flags=re.DOTALL)
        if fence:
            content = fence.group(1).strip()
    try:
        value = json.loads(content, object_pairs_hook=no_duplicates)
    except (json.JSONDecodeError, ValueError):
        return None, "invalid_json"
    if not isinstance(value, dict) or set(value) != {"answer"}:
        return None, "invalid_schema"
    if not isinstance(value["answer"], str) or value["answer"] not in legal_choices:
        return None, "illegal_choice"
    return value["answer"], None
