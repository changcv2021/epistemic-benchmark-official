"""Independent G1-X branches, auditable factorial overlays and minimal pairs."""

import copy

import difflib

import itertools

from collections import Counter

from epistemic_benchmark.utils.io import *

from epistemic_benchmark.data.development import build_worlds

PROFILES={'HH':(7,7),'LL':(4,4),'HL':(7,4),'LH':(4,7)}

MC_SYSTEM='Answer the question using only the supplied fictional case. Return only a JSON object with one key, "answer", whose value is the option letter. Do not include an explanation.'

COUNT_SYSTEM='Answer the question using only the supplied fictional case. Return exactly one integer from 0 to 8, with no JSON, words, or explanation.'

SUFFIX_TOKEN_TOLERANCE=8

def history(w, profile):
    rows=[]
    for s, count in zip(('O1','O2'), PROFILES[profile]):
        offset=(w['index']+(0 if s=='O1' else 3))%8
        correct={(offset+j)%8 for j in range(count)}
        for i in range(8):
            reported='A' if (i+w['index'])%2==0 else 'B'
            rows.append(dict(source=s, episode=f'{s}-H{i+1}', reported=reported,
                verified=reported if i in correct else ('B' if reported=='A' else 'A')))
    return rows

def history_text(w, rows):
    states=w['candidate_states']
    heading=(f"Earlier, separate cases in the same {w['domain'].replace('_',' ')} setting tested the same kind of attribute ({w['target_relation']}). "
             'All sixteen cases below occurred before today. Their trusted verification is complete. They are not observations of today\'s target.\n')
    return heading+'\n'.join(f"{r['episode']}: {r['source']} reported {states[r['reported']]}; trusted verification found {states[r['verified']]}." for r in rows)

def quality_text(w, quality):
    pairs={
      'photo_identifier':('The photograph shows the entire identifying tag and the state indicator.','The photograph shows only the first part of the identifying tag; the state indicator remains visible.'),
      'log_identifier':('The log extract retains the complete target identifier and the recorded value.','The log extract retains only the prefix of the target identifier; the recorded value remains visible.'),
      'document_identifier':('The document copy shows the complete case identifier and its value field.','The document copy masks the last part of the case identifier; its value field remains visible.'),
      'audio_identifier':('The audio clip preserves the complete spoken target identifier and the spoken value.','The audio clip loses the end of the spoken target identifier; the spoken value remains audible.')}
    return pairs[w['quality_operation']][0 if quality=='high' else 1]

def report_graph(w, mode='distinct', pattern='BB', c=None):
    donor=w['shared_root_donor']
    if c is not None:
        if c==0:return []
        first=dict(relay='M1',root='e1',source='O1',state='B')
        if c==1:return [first]
        if c==2:return [first,dict(first)]
        if c==3:return [first,{**first,'relay':'M2'}]
        graph=[first,dict(relay='M2',root='e2',source='O2',state='B')]
        if c in (5,6):graph[0]['state']='A'
        if c==6:graph.reverse()
        if c==7:
            for row in graph:row['state']='A'
        return graph
    if mode=='shared':
        require(pattern in ('AA','BB'),'One faithful shared root cannot disagree')
        return [dict(relay=m,root='e1' if donor=='O1' else 'e2',source=donor,state=pattern[j]) for j,m in enumerate(('M1','M2'))]
    return [dict(relay=m,root=f'e{j+1}',source=f'O{j+1}',state=pattern[j]) for j,m in enumerate(('M1','M2'))]

def wrap(w, block, text):
    # Moving archived paragraphs changes presentation, not the time of events or receipt.
    f=w['discourse_format']
    if f=='first_person_report':return f'Archivist\'s note, {block}: I transcribe the following record without adding observations.\n{text}'
    if f=='two_person_dialogue':return f'Archived dialogue entry [{block}]\nArchivist: Which record is attached?\nClerk: The following text is the attached record.\n{text}'
    if f=='group_chat':return f'Archived group-chat attachment [{block}] — posted by the records clerk:\n{text}'
    if f=='email_thread':return f'Archived email attachment\nFrom: records clerk\nSubject: {block}\n{text}'
    if f=='incident_report':return f'Incident report, attached section {block}\n{text}'
    if f=='timestamped_log':return f'Log extract [{block}] (timestamps inside each entry)\n{text}'
    if f=='handoff_notes':return f'Handoff note [{block}]\n{text}'
    if f=='meeting_minutes':return f'Minutes: clerk read the attached {block} record:\n{text}'
    if f=='task_update_thread':return f'Task thread, archived attachment [{block}]\n{text}'
    return f'The archivist supplied the following {block} record.\n{text}'

FILLER_SENTENCES = (
 'An unrelated visitor leaflet describes the building entrance and the public notice board.',
 'The leaflet lists a reception desk, a coat stand, and a place for blank feedback forms.',
 'Its layout uses a title line followed by ordinary paragraphs about visitor facilities.',
 'These administrative details contain no observation or report about the target attribute.')

def make_case(w, family, variant, profile='HH', quality='limited', mode='distinct', pattern='BB',
              text_order='A_first', event_time='12:00', suffix='NONE', c=None, option_order=None):
    h=history(w,profile);graph=report_graph(w,mode,pattern,c)
    states=w['candidate_states'];target=w['target_entity'];relation=w['target_relation']
    framing=(f"This fictional case concerns {target}. The attribute being compared is its {relation}. "
        f"The two candidate values are {states['A']} and {states['B']}. "
        'All event and receipt times below are on the same fictional day unless a different day is stated. '
        'Paragraph order is archive presentation order, not event order. '
        'The question concerns 14:00 today. No trusted verification at 14:00 is supplied.\n'
        +'Fixed attributes: '+ '; '.join(f'{k.replace("_"," ")}: {v}' for k,v in w['fixed_non_target_attributes'].items())+'.\n'
        +w['background_text']+'\n'+'; '.join(f'{k} is {v}' for k,v in w['source_names'].items())+'. '
        'M1 and M2 relay their cited records faithfully and add no observations of their own.')
    initial=wrap(w,'initial',f'The trusted initial record was made available at 10:00. It refers to 10:00 today: the {relation} of {target} was {states["A"]}.')
    reports=[]
    for r in graph:
        reports.append(f"Received at 13:00. {r['relay']} relays record {r['root']} from {r['source']}. "
            f"That record refers to {event_time} today and states: the {relation} of {target} was {states[r['state']]}. "
            f"{r['root']} is an observation by {r['source']}; {quality_text(w,quality)}")
    roots={r['root'] for r in graph}
    provenance=('The two distinct records were acquired separately; neither uses the other or a common upstream report.' if len(roots)==2 else
                'Every repeated citation of the same record refers to the same original observation.' if graph else '')
    report_text=wrap(w,'reports','\n'.join(reports)+ ('\n'+provenance if provenance else ''))
    # Padding only for C0/C1. Fixed before tokenization; report actual residual for each tokenizer.
    filler=''
    if c in (0,1):
        missing=2-len(graph)
        filler=wrap(w,'unrelated leaflet','\n'.join(FILLER_SENTENCES[:4 if missing==2 else 2]))
    segments={'framing':framing,'history':history_text(w,h),'initial':initial,'reports':report_text,'filler':filler,'suffix':''}
    if suffix=='COUNT_APPEND':
        n1,n2=PROFILES[profile]
        segments['suffix']=f'Appendix: O1 correct reports: {n1} of 8. O2 correct reports: {n2} of 8.'
    elif suffix=='SHAM_APPEND':
        segments['suffix']='Appendix: O1 listed reports: 8 of 8. O2 listed reports: 8 of 8.'
    order=['framing','history']+(['initial','reports'] if text_order=='A_first' else ['reports','initial'])+['filler','suffix']
    context='\n\n'.join(segments[s] for s in order if segments[s])
    graph_signature=digest({'reports':graph,'initial':{'state':'A','time':'10:00'},'report_time':event_time})
    return dict(case_id=f"{w['world_id']}.{family}.{variant}",world_id=w['world_id'],family=family,variant=variant,
        profile=profile,quality=quality,root_mode=mode,report_pattern=pattern,history=h,reports=graph,
        c_variant=c,option_order=option_order or w['default_option_order'],suffix=suffix,
        initial_record={'received_at':'10:00','refers_to_time':'10:00','presented_position':order.index('initial')},
        later_records={'received_at':'13:00','refers_to_time':event_time,'presented_position':order.index('reports')},
        segment_order=order,segments=segments,context=context,context_hash=digest(context),
        provenance_graph_signature=graph_signature,event_graph_signature=w['event_graph_signature'],
        renderer_id=w['renderer_id'],target_time='14:00',gold_p4=None)

def build(worlds=None):
    worlds=build_worlds() if worlds is None else worlds
    cases=[];previews=[];requests=[];labels=[];manifests=[]
    def add(w,case,probe,question,choices=None,gold=None,count=False,order=None):
        rid=case['case_id']+'.'+probe
        if count:
            system=COUNT_SYSTEM;mapping={};options={};suffix='\nReturn one integer from 0 to 8.'
        else:
            system=MC_SYSTEM
            choices=list(choices)
            if order is not None:choices=[choices[i] for i in order]
            options={chr(65+i):v[0] for i,v in enumerate(choices)}
            mapping={chr(65+i):v[1] for i,v in enumerate(choices)}
            suffix='\n'+'\n'.join(f'{k}. {v}' for k,v in options.items())
        messages=[{'role':'system','content':system},{'role':'user','content':case['context']+'\n\n'+question+suffix}]
        requests.append(dict(request_id=rid,messages=messages))
        manifests.append(dict(request_id=rid,case_id=case['case_id'],world_id=w['world_id'],family=case['family'],variant=case['variant'],
            relation_family=w['relation_family'],probe_id=probe,input_hash=digest(messages),context_hash=case['context_hash'],
            output_protocol='integer_0_8' if count else 'json_option_letter',question=question,options=options))
        labels.append(dict(request_id=rid,gold_answer=gold,choice_to_semantic_answer=mapping,has_gold=gold is not None))
    def p4(w,case):
        add(w,case,'P4',f"At 14:00 today, which candidate value for the {w['target_relation']} of {w['target_entity']} is better supported by the supplied evidence?",
            [(w['candidate_states'][s],s) for s in case['option_order']])
    for w in worlds:
        for i,(profile,quality,mode) in enumerate(itertools.product(('HH','LL'),('high','limited'),('distinct','shared')),1):
            previews.append(make_case(w,'CORE_PREVIEW',f'C{i}',profile,quality,mode))
        perm=list(itertools.permutations(range(4)))[w['index']%24]
        for profile,pattern in itertools.product(PROFILES,('BB','AB')):
            for suffix in ('NONE','COUNT_APPEND','SHAM_APPEND'):
                case=make_case(w,'R',f'{profile}.{pattern}.{suffix}',profile=profile,pattern=pattern,suffix=suffix)
                cases.append(case);p4(w,case)
                if suffix!='NONE':continue
                a,b=PROFILES[profile]
                for role,pid,gold in [('O1','P3a',a),('O2','P3b',b)]:
                    add(w,case,pid,f'In the eight fully verified earlier cases for {role}, how many reports matched their trusted verification?',gold=gold,count=True)
                add(w,case,'P3c','Across the supplied earlier verification records, which source had the higher observed proportion of correct reports?',
                    [('O1 had the higher proportion.','O1'),('O2 had the higher proportion.','O2'),('Their proportions were equal.','tie'),('There is insufficient verification information.','insufficient')],
                    'O1' if a>b else 'O2' if b>a else 'tie',order=perm)
        for order,time in itertools.product(('A_first','B_first'),('08:00','12:00')):
            case=make_case(w,'T',f'{order}.{time}',text_order=order,event_time=time)
            cases.append(case);p4(w,case)
            add(w,case,'CHECK','Which supplied target record refers to the later event time?',
                [('The initial record.','initial'),('The relayed records.','reports')], 'initial' if time=='08:00' else 'reports',order=[0,1] if w['index']%2==0 else [1,0])
        for pattern,order in itertools.product(('AA','BB'),('AB','BA')):
            case=make_case(w,'L',f'{pattern}.{order}',pattern=pattern,option_order=order)
            cases.append(case);p4(w,case)
            add(w,case,'CHECK',f'What value do the two relayed records state for the {w["target_relation"]} of {w["target_entity"]}?',
                [(w['candidate_states'][s],s) for s in w['default_option_order']],pattern[0])
        for c in range(8):
            case=make_case(w,'C',f'C{c}',c=c);cases.append(case);p4(w,case)
            root_count=len({r['root'] for r in case['reports']})
            choices=[('No original target observation root.','0'),('One original target observation root.','1'),('Two original target observation roots.','2')]
            shift=w['index']%3
            add(w,case,'CHECK','How many different original observation roots are cited by the later target reports? Count a repeated citation of one record only once; exclude the initial record.',
                choices,str(root_count),order=[(j+shift)%3 for j in range(3)])
    return dict(worlds=worlds,cases=cases,core_previews=previews,requests=requests,manifests=manifests,labels=labels)

def diff_cases(a,b):
    fields=[k for k in ('profile','quality','root_mode','report_pattern','history','reports','c_variant','option_order','suffix','initial_record','later_records','segment_order') if a[k]!=b[k]]
    return dict(from_case=a['case_id'],to_case=b['case_id'],changed_fields=fields,
        changed_segments=[k for k in a['segments'] if a['segments'][k]!=b['segments'][k]],
        unified_text_diff=''.join(difflib.unified_diff(a['context'].splitlines(True),b['context'].splitlines(True),fromfile=a['case_id'],tofile=b['case_id'])))

def minimal_pairs(bundle):
    cases={c['case_id']:c for c in bundle['cases']+bundle['core_previews']};pairs=[]
    for w in bundle['worlds']:
        wid=w['world_id']
        def pair(a,b):pairs.append(diff_cases(cases[wid+'.'+a],cases[wid+'.'+b]))
        for pattern in ('BB','AB'):
            for suffix in ('NONE','COUNT_APPEND','SHAM_APPEND'):
                pair(f'R.HL.{pattern}.{suffix}',f'R.LH.{pattern}.{suffix}')
                pair(f'R.HH.{pattern}.{suffix}',f'R.LL.{pattern}.{suffix}')
            for profile in PROFILES:
                for suffix in ('COUNT_APPEND','SHAM_APPEND'):
                    pair(f'R.{profile}.{pattern}.NONE',f'R.{profile}.{pattern}.{suffix}')
        for time in ('08:00','12:00'):pair(f'T.A_first.{time}',f'T.B_first.{time}')
        for order in ('A_first','B_first'):pair(f'T.{order}.08:00',f'T.{order}.12:00')
        for pattern in ('AA','BB'):pair(f'L.{pattern}.AB',f'L.{pattern}.BA')
        for order in ('AB','BA'):pair(f'L.AA.{order}',f'L.BB.{order}')
        for a,b in ((0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(4,7)):pair(f'C.C{a}',f'C.C{b}')
        for a,b in ((1,5),(2,6),(3,7),(4,8),(1,3),(2,4),(5,7),(6,8),(1,2),(3,4),(5,6),(7,8)):
            pair(f'CORE_PREVIEW.C{a}',f'CORE_PREVIEW.C{b}')
    return pairs

def validate(bundle):
    require(len(bundle['worlds'])==24,'Development world count')
    require(set(Counter(w['relation_family'] for w in bundle['worlds']).values())=={2},'Relation coverage')
    require([w['world_id'] for w in bundle['worlds']]==[f'XD{i:04}' for i in range(1,25)],'New ID namespace')
    require(all(not w['formal_eligible'] and not w['human_written'] and w['review_status']=='pending' for w in bundle['worlds']),'Review provenance')
    require(len(bundle['core_previews'])==192 and len(bundle['cases'])==960,'Context totals')
    require(len(bundle['requests'])==1920,'Request total')
    cases={c['case_id']:c for c in bundle['cases']}
    requests={r['request_id']:r for r in bundle['requests']}
    manifests={m['request_id']:m for m in bundle['manifests']}
    labels={l['request_id']:l for l in bundle['labels']}
    require(len(cases)==960 and len(requests)==1920,'Unique IDs')
    require(requests.keys()==manifests.keys()==labels.keys(),'Inventory match')
    for wid in (w['world_id'] for w in bundle['worlds']):
        mm=[m for m in manifests.values() if m['world_id']==wid]
        require(Counter(m['family'] for m in mm)=={'R':48,'T':8,'L':8,'C':16},'Within-world counts')
    for c in bundle['cases']+bundle['core_previews']:
        require(c['context_hash']==digest(c['context']),'Context hash')
        require(c['context']=='\n\n'.join(c['segments'][s] for s in c['segment_order'] if c['segments'][s]),'Rendered segments')
        counts=[sum(r['reported']==r['verified'] for r in c['history'] if r['source']==s) for s in ('O1','O2')]
        require(tuple(counts)==PROFILES[c['profile']],'History ground truth')
        roots={}
        for r in c['reports']:
            require(roots.get(r['root'],(r['source'],r['state']))==(r['source'],r['state']),'Inconsistent faithful root')
            roots[r['root']]=(r['source'],r['state'])
        require(c['gold_p4'] is None,'Invented P4 truth')
    for rid,r in requests.items():
        m=manifests[rid];l=labels[rid];c=cases[m['case_id']]
        require([v['role'] for v in r['messages']]==['system','user'],'Cross-branch leakage')
        require(r['messages'][1]['content'].startswith(c['context']+'\n\n'),'Input context mismatch')
        require(m['input_hash']==digest(r['messages']) and m['context_hash']==c['context_hash'],'Input hash')
        if m['probe_id']=='P4':require(l['gold_answer'] is None,'Main P4 gold')
        if m['probe_id'] in ('P3a','P3b'):
            require(type(l['gold_answer']) is int and 0<=l['gold_answer']<=8 and m['output_protocol']=='integer_0_8','Integer probe')
            role='O1' if m['probe_id']=='P3a' else 'O2'
            require(l['gold_answer']==sum(h['reported']==h['verified'] for h in c['history'] if h['source']==role),'Wrong count gold')
        if m['probe_id']=='P3c':
            a,b=PROFILES[c['profile']]
            require(l['gold_answer']==('O1' if a>b else 'O2' if b>a else 'tie'),'Wrong relative reliability gold')
            require(set(l['choice_to_semantic_answer'].values())=={'O1','O2','tie','insufficient'},'Relative reliability options')
        if m['probe_id']=='CHECK':
            expected=('initial' if c['later_records']['refers_to_time']<'10:00' else 'reports') if c['family']=='T' else c['report_pattern'][0] if c['family']=='L' else str(len({r['root'] for r in c['reports']}))
            require(l['gold_answer']==expected,'Wrong structural check gold')
        require(l['has_gold']==(l['gold_answer'] is not None),'Gold flag mismatch')
    for d in minimal_pairs(bundle):
        a,b=d['from_case'],d['to_case'];segments=set(d['changed_segments'])
        if '.T.' in a:
            require(segments==set() if a.split('.')[-1]==b.split('.')[-1] else segments=={'reports'},'T isolation')
        if '.L.' in a and a.split('.')[-2]==b.split('.')[-2]:require(not segments,'L option-only change')
        if a.endswith('.C.C5') and b.endswith('.C.C6'):
            require(cases[a]['reports']==list(reversed(cases[b]['reports'])) and segments=={'reports'},'C5/C6 order isolation')
        if '.R.' in a:
            if a.rsplit('.',1)[0]==b.rsplit('.',1)[0]:require(segments=={'suffix'},'Append-only')
            else:
                require(segments<= {'history','suffix'} and 'history' in segments,'Reliability isolation')
                require([(r['episode'],r['reported']) for r in cases[a]['history']]==[(r['episode'],r['reported']) for r in cases[b]['history']],'History reports changed')
        if '.CORE_PREVIEW.' in a:
            ca=next(c for c in bundle['core_previews'] if c['case_id']==a)
            cb=next(c for c in bundle['core_previews'] if c['case_id']==b)
            require(sum(ca[k]!=cb[k] for k in ('profile','quality','root_mode'))==1,'Core single-factor pairing')
            require(segments==({'history'} if ca['profile']!=cb['profile'] else {'reports'}),'Core overlay altered protected text')
    return dict(status='passed',worlds=24,requests_per_model=1920,requests_six_models=11520,contexts=960,core_preview_contexts=192,
        background_families=len({w['background_family'] for w in bundle['worlds']}),
        actual_normalized_event_graph_signatures=len({w['event_graph_signature'] for w in bundle['worlds']}),
        quality_operations=len({w['quality_operation'] for w in bundle['worlds']}),
        human_review='pending',formal_worlds_generated=0)
