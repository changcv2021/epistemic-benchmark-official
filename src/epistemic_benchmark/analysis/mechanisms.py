"""Complete prespecified reliability and update-policy panels on formal worlds."""

from collections import defaultdict,Counter

from statistics import mean

from epistemic_benchmark.analysis.statistics import policy_predictions

from epistemic_benchmark.analysis.diagnostics import stats

def paired(worlds,index,left,right,reps=2000,select=None):
    records=[];flips=[];bounds=[];eligible=0
    for w in worlds:
        wid=w['world_id']
        if select is not None and not select(wid):continue
        eligible+=1;a=index[wid+'.'+left];b=index[wid+'.'+right]
        av=int(a['semantic_answer']=='B') if a['valid'] else None
        bv=int(b['semantic_answer']=='B') if b['valid'] else None
        if av is not None and bv is not None:
            records.append((wid,bv-av));flips.append((wid,int(av!=bv)))
        bounds.append(((0 if bv is None else bv)-(1 if av is None else av),
                       (1 if bv is None else bv)-(0 if av is None else av)))
    return dict(direction='right_minus_left_in_B_choice',planned_worlds=len(worlds),eligible_worlds=eligible,
        valid_pairs=len(records),effect=stats(records,worlds,reps),flip_rate=stats(flips,worlds,reps),
        all_eligible_missing_bounds=[mean(b[j] for b in bounds) for j in (0,1)] if bounds else None,
        descriptive_response_selected_subset=select is not None)

def reliability(worlds,index,reps=2000):
    contrasts={};joint=[];relative={};tables={}
    for pattern in ('BB','AB'):
        for suffix in ('NONE','COUNT_APPEND','SHAM_APPEND'):
            contrasts[f'HL_to_LH.{pattern}.{suffix}']=paired(worlds,index,f'R.HL.{pattern}.{suffix}.P4',f'R.LH.{pattern}.{suffix}.P4',reps)
        contrasts[f'HL_to_LH.{pattern}.P3c_correct_pair_DESCRIPTIVE']=paired(worlds,index,
            f'R.HL.{pattern}.NONE.P4',f'R.LH.{pattern}.NONE.P4',reps,
            select=lambda wid:all(index[f'{wid}.R.{p}.{pattern}.NONE.P3c']['correct'] is True for p in ('HL','LH')))
        contrasts[f'LL_to_HH.{pattern}']=paired(worlds,index,f'R.LL.{pattern}.NONE.P4',f'R.HH.{pattern}.NONE.P4',reps)
        for profile in ('HH','LL','HL','LH'):
            for left,right in (('NONE','COUNT_APPEND'),('NONE','SHAM_APPEND'),('SHAM_APPEND','COUNT_APPEND')):
                contrasts[f'{left}_to_{right}.{profile}.{pattern}']=paired(worlds,index,
                    f'R.{profile}.{pattern}.{left}.P4',f'R.{profile}.{pattern}.{right}.P4',reps)
            countpairs=[];probes=defaultdict(list)
            for w in worlds:
                wid=w['world_id'];prefix=f'{wid}.R.{profile}.{pattern}.NONE.'
                a=index[prefix+'P3a'];b=index[prefix+'P3b']
                if a['status']==b['status']=='completed':
                    value=(wid,int(bool(a['correct']) and bool(b['correct'])));joint.append(value);countpairs.append(value)
                for probe in ('P3a','P3b','P3c','P4'):probes[probe].append(index[prefix+probe])
            relative[profile+'.'+pattern]=dict(planned=len(worlds),joint_exact_count_completed=len(countpairs),
                joint_exact_count_correct=sum(v for _,v in countpairs),joint_exact_count_accuracy=stats(countpairs,worlds,reps))
            for probe,rr in probes.items():
                tables[profile+'.'+pattern+'.'+probe]=dict(planned=len(rr),completed=sum(r['status']=='completed' for r in rr),
                    valid=sum(r['valid'] for r in rr),states=dict(Counter(r['outcome_state'] for r in rr)),
                    correct=sum(bool(r['correct']) for r in rr),semantic_answers=dict(Counter(str(r['semantic_answer']) for r in rr if r['valid'])))
    return dict(worlds=len(worlds),contrasts=contrasts,joint_exact_count=stats(joint,worlds,reps),
        counts_by_profile_pattern=relative,condition_tables=tables,
        interpretation='Independent behavioral availability and utilization measurements; selected P3c-correct results are descriptive, never same-pass internal state evidence.')

def policies(worlds,index,cases,reps=2000):
    contrasts={}
    for time in ('08:00','12:00'):
        contrasts['text_order_at_'+time]=paired(worlds,index,f'T.A_first.{time}.P4',f'T.B_first.{time}.P4',reps)
    for order in ('A_first','B_first'):
        contrasts['event_time_at_'+order]=paired(worlds,index,f'T.{order}.08:00.P4',f'T.{order}.12:00.P4',reps)
    for pattern in ('AA','BB'):
        contrasts['option_order_'+pattern]=paired(worlds,index,f'L.{pattern}.AB.P4',f'L.{pattern}.BA.P4',reps)
    for a,b in ((0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(4,7)):
        contrasts[f'C{a}_to_C{b}']=paired(worlds,index,f'C.C{a}.P4',f'C.C{b}.P4',reps)
    records=[];bounds=[]
    for w in worlds:
        wid=w['world_id'];values=[]
        for order,time in (('A_first','08:00'),('B_first','08:00'),('A_first','12:00'),('B_first','12:00')):
            row=index[f'{wid}.T.{order}.{time}.P4'];values.append(int(row['semantic_answer']=='B') if row['valid'] else None)
        weights=(1,-1,-1,1);known=sum(a*b for a,b in zip(weights,values) if b is not None)
        missing=[a for a,b in zip(weights,values) if b is None]
        if not missing:records.append((wid,known))
        bounds.append((known+sum(min(v,0) for v in missing),known+sum(max(v,0) for v in missing)))
    contrasts['text_order_x_event_time']=dict(planned_worlds=len(worlds),complete_worlds=len(records),
        effect=stats(records,worlds,reps),all_planned_missing_bounds=[mean(b[j] for b in bounds) for j in (0,1)] if bounds else None,
        definition='Text order effect at 12:00 minus text order effect at 08:00')
    ids={w['world_id'] for w in worlds};strategies=defaultdict(list);ties=Counter();planned=0;valid=0;condition_rows=defaultdict(list)
    for c in cases:
        if c['world_id'] not in ids or c['family'] not in ('T','L','C'):continue
        planned+=1;row=index[c['case_id']+'.P4'];valid+=row['valid']
        condition_rows[c['family']+'.'+c['variant']].append(row)
        for policy,prediction in policy_predictions(c).items():
            if prediction is None:ties[policy]+=1
            elif row['valid']:strategies[policy].append((row['world_id'],int(row['semantic_answer']==prediction)))
            else:strategies[policy]  # Preserve policy entry even when all model answers are invalid.
    condition_tables={key:dict(planned=len(rr),valid=sum(r['valid'] for r in rr),
        semantic_choices=dict(Counter(r['semantic_answer'] for r in rr if r['valid'])),states=dict(Counter(r['outcome_state'] for r in rr))) for key,rr in condition_rows.items()}
    return dict(worlds=len(worlds),contrasts=contrasts,condition_tables=condition_tables,
        strategy_agreement={k:dict(planned_cases=planned,valid_model_cases=valid,policy_ties=ties[k],
            jointly_scored_cases=len(v),agreement=stats(v,worlds,reps)) for k,v in strategies.items()},
        interpretation='Parameters fixed before outcomes; ties abstain. Agreement is coverage-dependent descriptive prediction, not identification of an internal policy.')

def analyze(bundle,rows,reps=2000):
    index={r['request_id']:r for r in rows};worlds=bundle['worlds']
    w2=[w for w in worlds if w['panels']['in_F2']];w3=[w for w in worlds if w['panels']['in_F3']]
    result={'F2_all':reliability(w2,index,reps),'F3_all':policies(w3,index,bundle['cases'],reps)}
    # Keep prespecified strata visible; use full contrasts, not outcome-selected cells.
    for key,selector in [(s,lambda w,s=s:w['split']==s) for s in ('core','structural','naturalistic')]+[
        ('relation:'+r,lambda w,r=r:w['relation_family']==r) for r in sorted({w['relation_family'] for w in worlds})]:
        result['F2_'+key]=reliability([w for w in w2 if selector(w)],index,reps)
        result['F3_'+key]=policies([w for w in w3 if selector(w)],index,bundle['cases'],reps)
    return result
