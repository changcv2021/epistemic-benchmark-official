"""Protected-fact rendering for formal candidates; no human-authorship claims."""

import copy

from epistemic_benchmark.utils.io import digest

from epistemic_benchmark.prompts.diagnostics import history, quality_text, wrap

from epistemic_benchmark.data.development import NAMES

def background_text(w):
    a,b=w['candidate_states']['A'],w['candidate_states']['B'];target=w['target_entity'];relation=w['target_relation']
    family=w['background_graph']['family']
    variants={
      'single_change':f'Yesterday a completed change established {a} as the {relation} of {target}. That entry describes yesterday, not the target time today.',
      'historical_return':f'Two days earlier, the {relation} of {target} was {b}. A return to {a} was completed yesterday. These are historical entries.',
      'temporary_intermediate':f'Earlier this week {target} used a third, temporary value for its {relation}. The temporary arrangement ended yesterday; it is neither of the two candidates being compared today.',
      'parallel_entity':f'Yesterday another item had the value {b} for the same kind of attribute. That item is separate from {target}; its entry makes no claim about today\'s target.',
      'proposal_not_activation':f'Yesterday a draft proposed {b} for the {relation} of {target}. The draft was archived without activation. A proposal alone does not establish an actual change.',
      'planned_vs_effective':f'Yesterday a planning note scheduled {b} as the {relation} of {target} for tomorrow. Its planned effective day is tomorrow, not today.',
      'conditional_release':f'Yesterday a policy allowed the {relation} of {target} to become {b} only after a signed release. The policy itself is not a release; no release is supplied as an established fact.',
      'alias_binding':f'Yesterday the archive assigned the label "{target.split()[-1]} alias" to {target}. Both labels identify the same target; the alias is not another item.',
      'scope_copy':f'Yesterday a training copy used {b} for its {relation}. The copy and the live target {target} are distinct, and the copy entry does not state the live target\'s current value.',
      'supersession_chain':f'A two-day-old record listed {b} for the {relation} of {target}. Yesterday that record was superseded by a replacement listing {a}. Neither entry is a verification of today\'s target time.'}
    return variants[family]

def diagnostic_world(w,index):
    return {**w,'index':index,'background_text':background_text(w),
        'source_names':{'O1':NAMES[index%12],'O2':NAMES[(index+5)%12],'M1':'Relay One','M2':'Relay Two'}}

def framing(w):
    a,b=w['candidate_states']['A'],w['candidate_states']['B'];setting=w['fixed_non_target_attributes']['case_setting']
    topic=f"{w['target_relation']} of {w['target_entity']}"
    templates={
     'third_person_narrative':f'At the {setting}, a coordinator gathered the records concerning the {topic}. The choice is between {a} and {b}.',
     'first_person_report':f'I am preparing a handoff at the {setting}. I need to decide which of two values, {a} or {b}, is supported for the {topic}. I have the records copied below.',
     'two_person_dialogue':f'Coordinator: We need to settle what the records support for the {topic}.\nClerk: The candidates are {a} and {b}. I have attached the records from the {setting}; my attachment adds no observation.',
     'group_chat':f'Operations chat, {setting}\nCoordinator: Please compare {a} with {b} for the {topic}.\nRecords clerk: I have attached the relevant entries below. I am only passing them along.',
     'email_thread':f'To: handoff team\nSubject: records to check before handoff\nPlease review the {topic} at the {setting}. The two values under consideration are {a} and {b}. The attached material is copied below.',
     'incident_report':f'Record review at the {setting}\nQuestion under review: {topic}.\nCandidate values: {a}; {b}.\nThe following entries form the supplied case record.',
     'timestamped_log':f'Archive extracts — {setting}\nTarget field: {topic}.\nCandidates retained for comparison: {a}; {b}.\nThe timestamps within entries identify their event and receipt times.',
     'handoff_notes':f'Handoff notes for the {setting}\nStill to check: {topic}. Compare {a} with {b}. The incoming team has the entries below, with their stated times and sources.',
     'meeting_minutes':f'Minutes of a record-review meeting at the {setting}\nThe chair asked the team to compare {a} and {b} for the {topic}. The clerk read the attached entries without adding an observation.',
     'task_update_thread':f'Task update — {setting}\nOpen item: determine which candidate is better supported for the {topic}: {a} or {b}. The attached entries are the available evidence.'}
    return templates[w['discourse_format']]+('\nThis is a fictional case. The question concerns 14:00 today. All event and receipt times are on this fictional day unless another day is explicitly stated. '
        'Paragraph order is archive presentation order, not event order. Mapped messengers copy their cited records faithfully and make no additional observations.\n'
        +'Fixed attributes: '+'; '.join(f'{k.replace("_"," ")}: {v}' for k,v in w['fixed_non_target_attributes'].items())+'.\n'+background_text(w))

def histories(w,profile):
    rows=history(w,profile)
    count=7 if profile=='HH' else 4
    for source in range(3,w['evidence_graph']['active_original_sources']+1):
        offset=(w['index']+3*(source-1))%8;correct={(offset+j)%8 for j in range(count)}
        for i in range(8):
            reported='A' if (i+w['index'])%2==0 else 'B'
            rows.append(dict(source=f'O{source}',episode=f'O{source}-H{i+1}',reported=reported,
                verified=reported if i in correct else ('B' if reported=='A' else 'A')))
    states=w['candidate_states']
    text=(f"The following {len(rows)} separate earlier cases concerned the same kind of attribute ({w['target_relation']}) in the same setting. "
        'Each source has eight fully verified cases. They all occurred before today and are not observations of today\'s target. '
        'Histories are retained even for an observer whose current record is not cited.\n')
    text+='\n'.join(f"{r['episode']}: {r['source']} reported {states[r['reported']]}; trusted verification found {states[r['verified']]}." for r in rows)
    return rows,text

def evidence_text(w,quality,root_mode):
    graph=w['evidence_graph'];messages=graph['final_messages'];root_key='distinct_root' if root_mode=='distinct' else 'shared_root'
    roots=sorted({m[root_key] for m in messages});edges=graph['distinct_edges' if root_mode=='distinct' else 'shared_edges']
    parents={b:a for a,b,kind in edges if kind in ('copies','cites')}
    nodes={n['id']:n for n in graph['nodes']};clauses=[]
    for root in roots:
        source='O'+root[1:]
        clauses.append(f'Record {root} is an observation by {source} referring to 12:00 today. {quality_text(w,quality)} '
            f'The record states that the {w["target_relation"]} of {w["target_entity"]} was {w["candidate_states"]["B"]}.')
    if len(roots)>1:clauses.append('These original records were acquired separately; none uses another original record or any common upstream report. This is a statement about record ancestry, not a claim that all possible errors are statistically independent.')
    else:clauses.append('All cited current evidence traces to this one original record; repeating or passing it along does not create a new observation.')
    for j,m in enumerate(messages,1):
        root=m[root_key];cursor=parents['relay_event_'+m['speaker']];chain=[]
        while cursor not in roots:
            node=nodes[cursor];chain.append(f'{cursor}, copied faithfully by {node.get("actor",cursor)}');cursor=parents[cursor]
        path=(' via '+', then '.join(reversed(chain))) if chain else ''
        clauses.append(f'Message {j}, received at 13:00: {m["speaker"]} relays {root}{path}. '
            f'The message states that at 12:00 the {w["target_relation"]} of {w["target_entity"]} was {w["candidate_states"]["B"]}. '
            f'In this message, {m["speaker"]} acts as a faithful messenger, not as an additional observer.')
    return '\n'.join(clauses),{'message_'+str(i+1):m[root_key] for i,m in enumerate(messages)},roots

def core_case(w,cid,profile,quality,root_mode,verified=None,initial_only=False):
    rows,h=histories(w,profile)
    initial=wrap(w,'initial',f'The trusted initial record was made available at 10:00. It refers to 10:00 today: the {w["target_relation"]} of {w["target_entity"]} was {w["candidate_states"]["A"]}.')
    evidence,bindings,roots=evidence_text(w,quality,root_mode)
    segments={'framing':framing(w),'history':h,'initial':initial,'reports':wrap(w,'reports',evidence),'verification':''}
    if initial_only:
        segments['history']='';segments['reports']=''
        # P0 contains an initial prefix only, without backgrounds that hint at a later target claim.
        segments['framing']=(f'This fictional case concerns the {w["target_relation"]} of {w["target_entity"]}. '
            f'The two candidate values are {w["candidate_states"]["A"]} and {w["candidate_states"]["B"]}.')
    if verified is not None:
        segments['verification']=(f'A separate trusted verification was completed and received at 14:00 today. '
            f'It directly verifies that at 14:00 the {w["target_relation"]} of {w["target_entity"]} was {w["candidate_states"][verified]}. '
            'This is a trusted verification of the target time, not a source report or a repetition of an earlier record.')
    context='\n\n'.join(v for v in segments.values() if v)
    return dict(case_id=f'{w["world_id"]}.{cid}',world_id=w['world_id'],family='F1',variant=cid,profile=profile,quality=quality,
        root_mode=root_mode,segments=segments,context=context,context_hash=digest(context),history=rows,
        bindings=bindings,root_count=len(roots),verified_state=verified,initial_only=initial_only,
        source_graph=w['evidence_graph'],target_time='14:00',gold_p4=verified)
