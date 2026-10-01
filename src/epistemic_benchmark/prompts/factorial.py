"""Formal candidate request inventory. This module never loads a model or submits a GPU job."""

import itertools

from collections import Counter

from epistemic_benchmark.utils.io import *

from epistemic_benchmark.prompts.diagnostics import MC_SYSTEM, build as diagnostic_build

from epistemic_benchmark.prompts.language import diagnostic_world, core_case

CONDITIONS={f'C{i}':v for i,v in enumerate(itertools.product(('HH','LL'),('high','limited'),('distinct','shared')),1)}

def build(worlds):
    cases=[];requests=[];manifests=[];labels=[];reuse=[]
    def add(w,c,probe,question,options,gold,module):
        rid=c['case_id']+'.'+probe
        visible={chr(65+i):text for i,(text,_) in enumerate(options)}
        mapping={chr(65+i):value for i,(_,value) in enumerate(options)}
        messages=[{'role':'system','content':MC_SYSTEM},{'role':'user','content':c['context']+'\n\n'+question+'\n'+'\n'.join(f'{k}. {v}' for k,v in visible.items())}]
        requests.append(dict(request_id=rid,messages=messages))
        manifests.append(dict(request_id=rid,case_id=c['case_id'],world_id=w['world_id'],split=w['split'],family=c['family'],
            variant=c['variant'],relation_family=w['relation_family'],probe_id=probe,formal_module=module,
            output_protocol='json_option_letter',question=question,options=visible,context_hash=c['context_hash'],input_hash=digest(messages),
            renderer_id=w['renderer_id'],event_graph_signature=w['event_graph_signature']))
        labels.append(dict(request_id=rid,gold_answer=gold,choice_to_semantic_answer=mapping,has_gold=gold is not None))
        return rid
    def states(w):return [(w['candidate_states'][s],s) for s in w['default_option_order']]
    def counts(w,c,probe,module):
        values={'O1':sum(r['reported']==r['verified'] for r in c['history'] if r['source']=='O1'),
                'O2':sum(r['reported']==r['verified'] for r in c['history'] if r['source']=='O2')}
        alternatives=[(f'O1: {a} of 8; O2: {b} of 8.',{'O1':a,'O2':b}) for a,b in ((7,7),(4,4),(7,4),(4,7))]
        perm=list(itertools.permutations(range(4)))[w['index']%24]
        return add(w,c,probe,'In the eight fully verified earlier cases for each of O1 and O2, how many reports matched verification for each source?',
                   [alternatives[j] for j in perm],values,module)
    for i,raw in enumerate(worlds):
        w=diagnostic_world(raw,i)
        for cid,(profile,quality,rootmode) in CONDITIONS.items():
            c=core_case(w,'CORE.'+cid,profile,quality,rootmode);cases.append(c)
            add(w,c,'P1',f'What value did the trusted initial record give for the {w["target_relation"]} of {w["target_entity"]} at 10:00?',states(w),'A','F1')
            alternatives=[]
            for mode,q in itertools.product(('distinct','shared'),('high','limited')):
                bindings={'message_'+str(j+1):m['distinct_root' if mode=='distinct' else 'shared_root'] for j,m in enumerate(w['evidence_graph']['final_messages'])}
                semantic=dict(bindings=bindings,root_count=len(set(bindings.values())),quality=q)
                text='; '.join(f'{k.replace("_"," ")} cites {v}' for k,v in bindings.items())
                text+='; identifying information is '+('complete.' if q=='high' else 'partly unavailable.')
                alternatives.append((text,semantic))
            perm=list(itertools.permutations(range(4)))[w['index']%24]
            add(w,c,'P2','Which option correctly matches the later messages to their original records and describes the identifying information available in those records?',
                [alternatives[j] for j in perm],dict(bindings=c['bindings'],root_count=c['root_count'],quality=quality),'F1')
            counts(w,c,'P3-HISTORY','F1')
            add(w,c,'P4',f'At 14:00 today, which candidate value for the {w["target_relation"]} of {w["target_entity"]} is better supported by the supplied evidence?',states(w),None,'F1')
        base=w['verified_base_condition'];profile,quality,mode=CONDITIONS[base]
        p0=core_case(w,'INITIAL_ONLY',profile,quality,mode,initial_only=True);cases.append(p0)
        add(w,p0,'P0',f'What value does the trusted initial record give for the {w["target_relation"]} of {w["target_entity"]} at 10:00?',states(w),'A','F1')
        for truth in ('A','B'):
            c=core_case(w,'VERIFIED_'+truth,profile,quality,mode,verified=truth);cases.append(c)
            rid=add(w,c,'D4',f'At 14:00 today, which candidate value for the {w["target_relation"]} of {w["target_entity"]} is better supported by the supplied evidence?',states(w),truth,'F1')
            if w['panels']['in_F4']:
                reuse.append(dict(world_id=w['world_id'],truth_version=truth,F4_D4_reuses_request_id=rid,
                    messages_hash=manifests[-1]['input_hash'],cache_policy='Reuse only the identical request within the same model revision, tokenizer/chat template, decoding profile and input hash. No cross-model or old-study reuse.'))
                add(w,c,'D1',f'What value does the trusted verification establish for the {w["target_relation"]} of {w["target_entity"]} at 14:00?',states(w),truth,'F4')
                alternatives=[]
                for verified_block,rootmode in itertools.product(('verification_at_14','initial_record_at_10'),('distinct','shared')):
                    bindings={'message_'+str(j+1):m['distinct_root' if rootmode=='distinct' else 'shared_root'] for j,m in enumerate(w['evidence_graph']['final_messages'])}
                    text=('The separate 14:00 verification' if verified_block=='verification_at_14' else 'The initial 10:00 record')+' establishes the target-time fact; '
                    text+='; '.join(f'{k.replace("_"," ")} relays {v}' for k,v in bindings.items())+'.'
                    alternatives.append((text,dict(verification_block=verified_block,bindings=bindings)))
                perm=list(itertools.permutations(range(4)))[w['index']%24]
                add(w,c,'D2','Which option identifies the trusted verification of the target time and the ancestry of the later source reports?',
                    [alternatives[j] for j in perm],dict(verification_block='verification_at_14',bindings=c['bindings']),'F4')
                counts(w,c,'D3','F4')
    selected=[diagnostic_world(w,i) for i,w in enumerate(worlds) if w['panels']['in_F2']]
    di=diagnostic_build(selected)
    windex={w['world_id']:w for w in worlds}
    keep={c['case_id'] for c in di['cases'] if c['family']=='R' or windex[c['world_id']]['panels']['in_F3']}
    for c in di['cases']:
        if c['case_id'] in keep:
            # Explicit module definition: fixed two-root diagnostics; not silently claiming to preserve every F1 structural graph.
            c['provenance_overlay']='frozen_G1_two_root_diagnostic_controls'
            cases.append(c)
    keep_rids={m['request_id'] for m in di['manifests'] if m['case_id'] in keep}
    requests.extend(r for r in di['requests'] if r['request_id'] in keep_rids)
    labels.extend(l for l in di['labels'] if l['request_id'] in keep_rids)
    for m in di['manifests']:
        if m['request_id'] in keep_rids:
            w=windex[m['world_id']]
            manifests.append({**m,'split':w['split'],'formal_module':'F2' if m['family']=='R' else 'F3',
                'renderer_id':w['renderer_id'],'event_graph_signature':w['event_graph_signature']})
    return dict(worlds=worlds,cases=cases,requests=requests,manifests=manifests,labels=labels,reuse=reuse)

def validate(bundle):
    requests={r['request_id']:r for r in bundle['requests']};cases={c['case_id']:c for c in bundle['cases']}
    manifests={m['request_id']:m for m in bundle['manifests']};labels={l['request_id']:l for l in bundle['labels']}
    require(len(requests)==len(bundle['requests'])==41020,'Formal logical request count')
    require(len(cases)==len(bundle['cases'])==16540,'Formal context count')
    require(requests.keys()==manifests.keys()==labels.keys(),'Formal inventory alignment')
    require(Counter(m['formal_module'] for m in manifests.values())=={'F1':17500,'F2':14400,'F3':7680,'F4':1440},'Module arithmetic')
    for rid,r in requests.items():
        m=manifests[rid];c=cases[m['case_id']];l=labels[rid]
        require([x['role'] for x in r['messages']]==['system','user'],'Probe-context leakage')
        require(m['input_hash']==digest(r['messages']) and m['context_hash']==digest(c['context']),'Input or context hash')
        require(r['messages'][1]['content'].startswith(c['context']+'\n\n'),'Incorrect branch input')
        if m['probe_id']=='P4':require(l['gold_answer'] is None,'Unsupported unique gold for main choice')
        if m['probe_id'] in ('P1','P0'):require(l['gold_answer']=='A','Initial fact gold')
        if m['probe_id'] in ('D1','D4'):require(l['gold_answer']==c['verified_state'],'Verification fact gold')
        if m['probe_id'] in ('P3-HISTORY','D3'):
            gold={s:sum(h['reported']==h['verified'] for h in c['history'] if h['source']==s) for s in ('O1','O2')}
            require(l['gold_answer']==gold,'Incorrect historical count gold')
        if m['probe_id']=='P2':require(l['gold_answer']=={'bindings':c['bindings'],'root_count':c['root_count'],'quality':c['quality']},'P2 binding/quality gold')
        if m['probe_id'] in ('P3a','P3b'):
            role='O1' if m['probe_id']=='P3a' else 'O2'
            require(l['gold_answer']==sum(h['reported']==h['verified'] for h in c['history'] if h['source']==role),'Incorrect independent count gold')
        if m['probe_id']=='P3c':
            a,b=[sum(h['reported']==h['verified'] for h in c['history'] if h['source']==s) for s in ('O1','O2')]
            require(l['gold_answer']==('O1' if a>b else 'O2' if b>a else 'tie'),'Incorrect relative reliability gold')
        if m['probe_id']=='D2':require(l['gold_answer']=={'verification_block':'verification_at_14','bindings':c['bindings']},'D2 fact/source gold')
        if m['probe_id']=='CHECK':
            expected=('initial' if c['later_records']['refers_to_time']<'10:00' else 'reports') if c['family']=='T' else c['report_pattern'][0] if c['family']=='L' else str(len({r['root'] for r in c['reports']}))
            require(l['gold_answer']==expected,'Incorrect diagnostic fact gold')
    for w in bundle['worlds']:
        a=cases[w['world_id']+'.VERIFIED_A'];b=cases[w['world_id']+'.VERIFIED_B']
        require({k for k in a['segments'] if a['segments'][k]!=b['segments'][k]}=={'verification'},'Truth control changed non-verification text')
        for c in (a,b):require(c['variant'].startswith('VERIFIED_'),'Invalid truth ID')
        core=[cases[f'{w["world_id"]}.CORE.C{i}'] for i in range(1,9)]
        for i,j,factor in [(0,4,'R'),(1,5,'R'),(2,6,'R'),(3,7,'R'),(0,2,'Q'),(1,3,'Q'),(4,6,'Q'),(5,7,'Q'),(0,1,'I'),(2,3,'I'),(4,5,'I'),(6,7,'I')]:
            changed={k for k in core[i]['segments'] if core[i]['segments'][k]!=core[j]['segments'][k]}
            require(changed==({'history'} if factor=='R' else {'reports'}),'Non-minimal core factorial pair')
    require(len(bundle['reuse'])==480,'F4 D4 reuse count')
    for item in bundle['reuse']:
        rid=item['F4_D4_reuses_request_id'];require(manifests[rid]['probe_id']=='D4' and manifests[rid]['formal_module']=='F1','Incorrect D4 reuse target')
        require(item['messages_hash']==digest(requests[rid]['messages']),'D4 cache input mismatch')
    return dict(status='AUTOMATIC_REQUEST_VALIDATION_PASSED_CANDIDATE_ONLY',worlds=500,contexts=len(cases),requests_per_model=41020,
        planned_six_model_requests=246120,counts_by_module=dict(Counter(m['formal_module'] for m in manifests.values())),
        D4_reuse_entries=480,independent_branches=True,all_core_minimal_pairs_passed=True,
        human_review='pending',naturalistic_rewrite='pending',token_audit='pending',formal_gpu_authorized=False)
