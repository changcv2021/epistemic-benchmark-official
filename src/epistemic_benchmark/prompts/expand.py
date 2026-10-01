from epistemic_benchmark.utils.io import digest, require
from epistemic_benchmark.prompts.diagnostics import build as diagnostic_build
from epistemic_benchmark.prompts.language import diagnostic_world
from epistemic_benchmark.prompts.naturalistic import transform_case
from epistemic_benchmark.prompts.padding import pad_controls

def select_tasks(w):
    wid=w['world_id'];tasks=[]
    tasks += [('T1','C'+str(i),f'{wid}.CORE.C{i}.P4') for i in range(1,9)]
    tasks += [('T2',p,f'{wid}.R.{p}.AB.NONE.P4') for p in ('HL','LH')]
    tasks += [('T3',o+'.'+t,f'{wid}.T.{o}.{t}.P4') for o in ('A_first','B_first') for t in ('08:00','12:00')]
    tasks += [('T4','S'+str(i),f'{wid}.C.C{i}.P4') for i in range(1,5)]
    tasks += [('T5',t,f'{wid}.VERIFIED_{t}.D4') for t in ('A','B')]
    require(len(tasks)==20,'Wrong task inventory');return tasks

def expanded_diagnostics(w,index,style,padding_tokenizer,profile):
    dw=diagnostic_world(w,index);d=diagnostic_build([dw])
    cases={c['case_id']:c for c in d['cases']};requests={r['request_id']:r for r in d['requests']}
    manifests={m['request_id']:m for m in d['manifests']}
    if w['split']=='naturalistic':
        for c in d['cases']:
            before=c['context'];transform_case(w,c,style)
            for m in d['manifests']:
                if m['case_id']==c['case_id']:
                    r=requests[m['request_id']];prefix=before+'\n\n'
                    require(r['messages'][1]['content'].startswith(prefix),'Naturalistic branch prefix changed')
                    r['messages'][1]['content']=c['context']+'\n\n'+r['messages'][1]['content'][len(prefix):]
                    m.update(context_hash=c['context_hash'],input_hash=digest(r['messages']))
    pad_controls(d,padding_tokenizer,profile)
    return cases,requests,manifests,{r['request_id']:r for r in d['labels']}
