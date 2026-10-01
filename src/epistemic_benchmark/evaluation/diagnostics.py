"""Formal semantic subscoring; invalid protocol output never becomes a state choice."""

from epistemic_benchmark.utils.io import require

from epistemic_benchmark.evaluation.scoring import score as base_score

def components(probe, predicted, gold, valid):
    if probe=='P2':
        keys=('bindings','root_count','quality')
    elif probe=='D2':
        keys=('verification_block','bindings')
    elif probe in ('P3-HISTORY','D3'):
        keys=('O1','O2')
    else:
        return {}
    require(isinstance(gold,dict) and all(k in gold for k in keys),'Missing component labels')
    result={k:bool(valid and isinstance(predicted,dict) and predicted.get(k)==gold[k]) for k in keys}
    if 'bindings' in keys:
        result.update({'binding:'+message:bool(valid and isinstance(predicted,dict) and
                      predicted.get('bindings',{}).get(message)==root) for message,root in gold['bindings'].items()})
    return result

def score(bundle,attempts):
    rows=base_score(bundle,attempts)
    manifests={m['request_id']:m for m in bundle['manifests']}
    labels={l['request_id']:l for l in bundle['labels']}
    for row in rows:
        m=manifests[row['request_id']];label=labels[row['request_id']]
        row.update({k:m[k] for k in ('formal_module','split','renderer_id','event_graph_signature')})
        row['component_correct']=components(row['probe_id'],row['semantic_answer'],label['gold_answer'],row['valid'])
        row['component_scoring_note']='Protocol-inclusive components; summarize only technically completed responses; valid-only rates reported separately.'
    return rows

def cache_key(request,model_identity,profile):
    """Exact same-model D4 reuse only; changing any measurement identity changes the key."""
    from epistemic_benchmark.utils.io import digest
    required=('repo_id','revision','weights_sha256_manifest','tokenizer_hash','chat_template_hash','runtime_fingerprint')
    require(all(model_identity.get(k) for k in required),'Incomplete cache model identity')
    return digest(dict(messages=request['messages'],model={k:model_identity[k] for k in required},profile=profile))
