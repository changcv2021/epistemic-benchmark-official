"""Frozen candidate protocols: raw integer counts and legacy strict JSON choices."""

import re

from epistemic_benchmark.evaluation.parser import parse_answer

from epistemic_benchmark.evaluation.attempts import validate_attempts

def parse(content, protocol, choices):
    if protocol=='integer_0_8':
        if isinstance(content,str) and re.fullmatch(r'[0-8]',content.strip()):
            return int(content.strip()),None
        return None,'invalid_integer_0_8'
    if protocol=='json_option_letter':
        return parse_answer(content,choices)
    raise ValueError('Unknown protocol')

def score(bundle, attempts):
    requests={r['request_id']:r for r in bundle['requests']}
    history=validate_attempts(attempts,requests)
    labels={l['request_id']:l for l in bundle['labels']}
    output=[]
    for m in bundle['manifests']:
        rid=m['request_id'];label=labels[rid]
        row={k:m[k] for k in ('request_id','case_id','world_id','family','variant','relation_family','probe_id','output_protocol')}
        row.update(status='not_run',valid=False,correct=None,has_gold=label['has_gold'],
            answer=None,semantic_answer=None,technical_error=False,truncated=False,
            invalid_format=False,protocol_violation=False,parse_error=None)
        if history[rid]:
            last=history[rid][-1];row['status']=last['status']
            row['technical_error']=last['status']!='completed'
            decoded=last.get('decoded')
            if decoded is not None:
                answer,error=parse(decoded['content'],m['output_protocol'],label['choice_to_semantic_answer'])
                violation=bool(decoded.get('reasoning_content')) or bool(last.get('runtime_violations'))
                valid=answer is not None and decoded['finish_reason']=='stop' and not violation
                semantic=(answer if m['output_protocol']=='integer_0_8' else label['choice_to_semantic_answer'].get(answer)) if valid else None
                row.update(valid=valid,answer=answer,semantic_answer=semantic,parse_error=error,
                    correct=(valid and semantic==label['gold_answer']) if label['has_gold'] else None,
                    invalid_format=error is not None,truncated=decoded['finish_reason']=='length',
                    protocol_violation=violation,usage=decoded.get('usage'))
        # Mutually exclusive headline categories, with overlapping raw flags also retained.
        row['outcome_state']=('not_run' if row['status']=='not_run' else 'technical_failure' if row['technical_error'] else
            'truncated' if row['truncated'] else 'protocol_violation' if row['protocol_violation'] else
            'invalid_format' if not row['valid'] else 'valid_wrong' if row['has_gold'] and not row['correct'] else
            'valid_correct' if row['has_gold'] else 'valid_choice')
        output.append(row)
    return output
