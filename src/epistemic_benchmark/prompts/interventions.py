"""Deterministic intervention renderers: no model-generated text and no answer summaries."""

from collections import Counter

from epistemic_benchmark.utils.intervention import *

from epistemic_benchmark.prompts.diagnostics import MC_SYSTEM, quality_text

def facts(w,c):
    result=[]
    def add(group,key,value,sentence,origin):
        result.append(dict(group=group,key=key,value=value,sentence=sentence,origin=origin))
    for s in sorted({h['source'] for h in c['history']}):
        history=[h for h in c['history'] if h['source']==s]
        require(len(history)==8,'Historical denominator changed')
        n=sum(h['reported']==h['verified'] for h in history)
        add('Source '+s,'Historical record',dict(source=s,correct=n,total=8),
            f'{s} had {n} of 8 previous reports match their completed trusted verification.', 'history:reported_equals_verified')
    if c['family']=='F1':
        bindings=c['bindings'];roots=sorted(set(bindings.values()))
        graph=c['source_graph'];active_edges=graph['distinct_edges' if c['root_mode']=='distinct' else 'shared_edges']
        parents={b:a for a,b,k in active_edges if k in ('copies','cites')}
        reports=[]
        for j,message in enumerate(graph['final_messages'],1):
            relay=message['speaker'];root=bindings['message_'+str(j)];cursor=parents['relay_event_'+relay];chain=[]
            while cursor!=root:
                chain.append(cursor);cursor=parents[cursor]
            reports.append(dict(relay=relay,root=root,source='O'+root[1:],chain=list(reversed(chain))))
        event_time='12:00'
    else:
        reports=[dict(r,chain=[]) for r in c['reports']];roots=sorted({r['root'] for r in reports})
        event_time=c['later_records']['refers_to_time']
    for root in roots:
        source=next(r['source'] for r in reports if r['root']==root)
        group='Record '+root
        add(group,'Origin',dict(root=root,source=source),f'{root} is an observation record from {source}.','reports:origin')
        qtext=quality_text(w,c['quality'])
        add(group,'Current evidence quality',dict(root=root,quality=c['quality'],operation=w['quality_operation']),f'For {root}, '+qtext[0].lower()+qtext[1:],'reports:quality_text')
        add(group,'Reported event time',dict(root=root,event_time=event_time),f'{root} concerns an event at {event_time} today.','reports:refers_to_time')
    for j,r in enumerate(reports,1):
        value=dict(message=j,speaker=r['relay'],root=r['root'],archive_chain=r['chain'],received_at='13:00')
        path=(' through the faithful archive transfers '+', then '.join(r['chain'])) if r['chain'] else ''
        add('Message '+str(j),'Evidence path',value,
            f'Message {j}, received at 13:00, is relayed by {r["relay"]} from {r["root"]}{path}; the relay adds no observation.', 'reports:faithful_path')
    statement=('The cited original records were acquired separately, without another cited record or a common upstream report as their source.' if len(roots)>1 else
        'All the cited later messages trace to one original observation record; repeated citations of that record are the same observation.')
    add('Evidence relationship','Ancestry',dict(cited_roots=roots,ancestry='separate' if len(roots)>1 else 'shared'),statement,'reports:explicit_ancestry_statement')
    add('Initial record','Event and receipt times',dict(event_time='10:00',received_at='10:00',trusted=True),
        'The trusted initial record concerns 10:00 today and was available at 10:00.','initial:trusted_and_times')
    if c.get('verified_state') is not None:
        add('Verification','Event and receipt times',dict(event_time='14:00',received_at='14:00',trusted=True),
            'A separate trusted verification directly concerns 14:00 today and was received at 14:00.','verification:trusted_and_times_only')
    require(len(result)==len({(r['group'],r['key']) for r in result}),'Duplicate fact identifier')
    # No state, candidate text, final answer or relative ranking enters the appendix.
    require(all('state' not in r['value'] and 'gold' not in r['value'] for r in result),'Answer leakage in fact_set')
    return result

def render_flat(fact_set):return ' '.join(r['sentence'] for r in fact_set)

def render_ledger(fact_set):
    output=['Epistemic Information'];last=None
    for f in fact_set:
        if f['group']!=last:output+=['',f['group']];last=f['group']
        output.append('- '+f['key']+': '+f['sentence'])
    return '\n'.join(output)

def validate_renderers(fact_set,flat,ledger):
    recovered=[s.split(': ',1)[1] for s in ledger.splitlines() if s.startswith('- ')]
    require(recovered==[f['sentence'] for f in fact_set],'Ledger omitted or added facts')
    require(flat==' '.join(recovered),'Flat/Ledger rendered factual content differs')
    require(not any(x in flat.lower() for x in ('therefore','choose a','choose b','more trustworthy','should be believed','stronger evidence supports')),'Answer recommendation leakage')

def sham(w,c,padding):
    parts=['Context organization']
    for s in sorted({h['source'] for h in c['history']}):
        parts+=['','Source '+s,'- Source identifier: '+s+'.','- Section label: source entry.']
    parts+=['','Current task','- Target entity: '+w['target_entity']+'.','- Two candidate states are under consideration.','', 'Document layout']
    parts+=['- Layout note: This is an additional line in this appendix.']*padding
    return '\n'.join(parts)

def matched_sham(w,c,ledger,tokenizers):
    targets=[len(t.encode(ledger,add_special_tokens=False)) for t in tokenizers]
    seed=sham(w,c,0);base=[len(t.encode(seed,add_special_tokens=False)) for t in tokenizers]
    line='- Layout note: This is an additional line in this appendix.'
    step=[max(1,len(t.encode('\n'+line,add_special_tokens=False))) for t in tokenizers]
    guess=max(0,round(sum((a-b)/s for a,b,s in zip(targets,base,step))/len(targets)))
    choices=[]
    for padding in range(max(0,guess-3),guess+4):
        candidate=sham(w,c,padding);counts=[len(t.encode(candidate,add_special_tokens=False)) for t in tokenizers]
        delta=max(abs(a-b)/b for a,b in zip(counts,targets));choices.append((delta,padding,candidate,counts))
    delta,padding,text,counts=min(choices)
    require(delta<=.10,'Cannot match sham within 10% on every actual tokenizer')
    return text,dict(padding_lines=padding,max_relative_token_difference=delta,sham_tokens=counts,ledger_tokens=targets)

def append_request(baseline,context,appendix):
    require(baseline['messages'][0]==dict(role='system',content=MC_SYSTEM),'Changed system prompt')
    if not appendix:return [dict(m) for m in baseline['messages']]
    prefix=context+'\n\n';user=baseline['messages'][1]['content']
    require(user.startswith(prefix),'C0 question prefix mismatch')
    # Preserve the final question and option order; appendix goes between evidence and question.
    return [dict(baseline['messages'][0]),dict(role='user',content=context+'\n\n'+appendix+'\n\n'+user[len(prefix):])]
