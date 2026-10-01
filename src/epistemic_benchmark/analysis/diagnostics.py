"""Formal paired effects, explicit missingness, and independent-branch verification."""

import random

from collections import defaultdict,Counter

from statistics import mean

from epistemic_benchmark.utils.io import SEED, require

from epistemic_benchmark.analysis.statistics import estimate

from epistemic_benchmark.analysis.design import coefficients

def stratified_estimate(records,worlds,reps=2000):
    grouped=defaultdict(list)
    for wid,value in records:grouped[wid].append(value)
    values={wid:mean(v) for wid,v in grouped.items()}
    relations={w['world_id']:w['relation_family'] for w in worlds};strata=defaultdict(list)
    for wid,v in values.items():strata[relations[wid]].append(v)
    if not values:return dict(estimate=None,ci95=None,worlds=0,observations=0,centered_bootstrap_p=None)
    center=mean(values.values());rng=random.Random(SEED);draws=[]
    if len(values)>1:
        for _ in range(reps):
            draws.append(mean(v for group in strata.values() for v in rng.choices(group,k=len(group))))
        draws.sort()
    return dict(estimate=center,ci95=[draws[int(.025*reps)],draws[int(.975*reps)-1]] if draws else None,
        worlds=len(values),observations=len(records),relation_stratum_counts={r:len(v) for r,v in strata.items()},
        centered_bootstrap_p=(1+sum(abs(d-center)>=abs(center)-1e-14 for d in draws))/(reps+1) if draws else None,
        degenerate_bootstrap=bool(draws and draws[0]==draws[-1]),
        method='Mean of world averages; within-relation world bootstrap conditional on observed usable counts. P is two-sided centered-bootstrap approximation.',
        caution='Missingness can change the observed relation mix; no missing-at-random claim. Degenerate intervals are empirical, not population certainty.')

def stats(records,worlds,reps=2000):
    renderer={w['world_id']:w['renderer_id'] for w in worlds}
    event={w['world_id']:w['event_graph_signature'] for w in worlds}
    return dict(world=stratified_estimate(records,worlds,reps),
        renderer_sensitivity=estimate(records,renderer,reps),event_graph_sensitivity=estimate(records,event,reps))

def factorial(worlds,index,reps=2000):
    result={};planned=len(worlds)
    definitions=coefficients()
    for quality,active in (('high',('C1','C2','C5','C6')),('limited',('C3','C4','C7','C8'))):
        definitions['I_at_'+quality]={c:(1 if c in ('C1','C3','C5','C7') else -1)/2 if c in active else 0 for c in definitions['I']}
    for name,weights in definitions.items():
        effects=[];bounds=[]
        for w in worlds:
            values={c:index[w['world_id']+'.CORE.'+c+'.P4'] for c in weights}
            ys={c:int(row['semantic_answer']=='B') if row['valid'] else None for c,row in values.items()}
            if all(y is not None for y in ys.values()):
                effects.append((w['world_id'],sum(weights[c]*ys[c] for c in weights)))
            known=sum(weights[c]*y for c,y in ys.items() if y is not None)
            unknown=[weights[c] for c,y in ys.items() if y is None]
            bounds.append((known+sum(min(0,v) for v in unknown),known+sum(max(0,v) for v in unknown)))
        result[name]=dict(planned_worlds=planned,complete_eight_condition_worlds=len(effects),
            coefficients=weights,effect=stats(effects,worlds,reps),world_effects=[dict(world_id=w,effect=v) for w,v in effects],
            all_planned_missing_bounds=[mean(b[j] for b in bounds) for j in (0,1)] if bounds else None)
    return result

def summary(rows,worlds,reps=2000):
    completed=[r for r in rows if r['status']=='completed'];valid=[r for r in rows if r['valid']]
    gold=[r for r in completed if r['has_gold']]
    component_keys=sorted({k for r in rows for k in r.get('component_correct',{})})
    return dict(planned=len(rows),completed=len(completed),valid=len(valid),states=dict(Counter(r['outcome_state'] for r in rows)),
        format_valid_completed_denominator=len(completed),format_valid_completed=sum(r['valid'] for r in completed),
        gold_completed=len(gold),correct=sum(bool(r['correct']) for r in gold),
        semantic_answer_counts=dict(Counter(str(r['semantic_answer']) for r in valid)),
        protocol_inclusive_accuracy=stats([(r['world_id'],int(bool(r['correct']))) for r in gold],worlds,reps),
        semantic_accuracy_valid_only=stats([(r['world_id'],int(bool(r['correct']))) for r in gold if r['valid']],worlds,reps),
        component_scores={k:dict(completed_denominator=sum(k in r.get('component_correct',{}) for r in completed),
            valid_denominator=sum(k in r.get('component_correct',{}) for r in valid),
            correct=sum(r.get('component_correct',{}).get(k,False) for r in completed)) for k in component_keys})

def ratio_interval(records,reps=2000):
    """Bootstrap pooled conditional ratio by whole world, preserving both truth variants."""
    grouped=defaultdict(lambda:[0,0])
    for w,n,d in records:grouped[w][0]+=n;grouped[w][1]+=d
    numer=sum(v[0] for v in grouped.values());denom=sum(v[1] for v in grouped.values())
    out=dict(numerator=numer,denominator=denom,estimate=numer/denom if denom else None,
        worlds_with_positive_denominator=sum(v[1]>0 for v in grouped.values()),planned_world_clusters=len(grouped),
        ci95=None,bootstrap_zero_denominator_draws=0,
        method='Resample whole worlds and recompute pooled numerator/denominator; retain both verified variants together.')
    if not denom:return out
    rng=random.Random(SEED);draws=[];groups=list(grouped.values())
    for _ in range(reps):
        sampled=rng.choices(groups,k=len(groups));d=sum(v[1] for v in sampled)
        if d:draws.append(sum(v[0] for v in sampled)/d)
    out['bootstrap_zero_denominator_draws']=reps-len(draws)
    if draws and len(groups)>1:
        draws.sort();out['ci95']=[draws[int(.025*len(draws))],draws[int(.975*len(draws))-1]]
        out['degenerate_bootstrap']=draws[0]==draws[-1]
    return out

def verified_separation(worlds,index,reps=2000):
    selected=[w for w in worlds if w['panels']['in_F4']];table=[];observed=[];inclusive=[];all_k=[]
    for w in selected:
        wid=w['world_id']
        for truth in ('A','B'):
            branches={p:index[wid+'.VERIFIED_'+truth+'.'+p] for p in ('D1','D2','D3','D4')}
            k=all(branches[p]['correct'] is True for p in ('D1','D2','D3'));d4=branches['D4']
            valid_wrong=k and d4['valid'] and d4['correct'] is False
            table.append(dict(world_id=wid,truth=truth,K=k,D4_valid=d4['valid'],D4_status=d4['status'],
                D4_correct=d4['correct'],K_and_valid_D4_wrong=valid_wrong))
            observed.append((wid,int(valid_wrong),int(k and d4['valid'])))
            inclusive.append((wid,int(k and d4['status']=='completed' and not d4['correct']),int(k and d4['status']=='completed')))
            all_k.append((wid,int(valid_wrong),int(k)))
    return dict(planned_worlds=len(selected),planned_truth_variants=2*len(selected),K=sum(r['K'] for r in table),
        conditional_valid_semantic_error=ratio_interval(observed,reps),
        conditional_protocol_inclusive_failure=ratio_interval(inclusive,reps),
        observed_valid_error_over_all_K=ratio_interval(all_k,reps),
        K_with_missing_or_invalid_D4=sum(r['K'] and not r['D4_valid'] for r in table),rows=table,
        interpretation='K combines independently correct behavioral probes. It is not the internal knowledge state of the D4 forward pass; K=0 is NA.')

def holm(pvalues,planned_family_size):
    available=sorted((p,k) for k,p in pvalues.items() if p is not None)
    require(planned_family_size>=len(pvalues),'Multiple-test family silently reduced')
    output={k:None for k in pvalues};previous=0.
    for i,(p,k) in enumerate(available):
        require(0<=p<=1,'Invalid p-value');previous=max(previous,min(1.,(planned_family_size-i)*p));output[k]=previous
    return output

def analyze(bundle,rows,reps=2000):
    index={r['request_id']:r for r in rows}
    require(len(index)==len(rows)==len(bundle['requests'])==41020,'Incomplete formal scoring denominator')
    worlds=bundle['worlds'];subsets={'core':[w for w in worlds if w['split']=='core'],'all':worlds}
    subsets.update({s:[w for w in worlds if w['split']==s] for s in ('structural','naturalistic')})
    subsets.update({'relation:'+rel:[w for w in worlds if w['relation_family']==rel] for rel in sorted({w['relation_family'] for w in worlds})})
    f1={key:factorial(ww,index,reps) for key,ww in subsets.items()}
    probe_summaries={}
    groups=defaultdict(list)
    for r in rows:groups[r['formal_module'],r['family'],r['probe_id']].append(r)
    for key,rr in groups.items():probe_summaries['.'.join(key)]=summary(rr,worlds,reps)
    conditions={}
    for c in range(1,9):
        rr=[r for r in rows if r['family']=='F1' and r['variant']==f'CORE.C{c}' and r['probe_id']=='P4']
        conditions[f'C{c}']=dict(planned=len(rr),valid=sum(r['valid'] for r in rr),
            semantic_choices=dict(Counter(r['semantic_answer'] for r in rr if r['valid'])),states=dict(Counter(r['outcome_state'] for r in rr)))
    return dict(planned=41020,worlds=500,states=dict(Counter(r['outcome_state'] for r in rows)),
        F1_factorial=f1,F1_eight_condition_choices=conditions,probe_summaries=probe_summaries,
        F4_separation=verified_separation(worlds,index,reps),bootstrap_repetitions=reps,
        primary_family='Six model Q_x_I effects on core300; apply Holm only after all six model estimates are collected.',
        limitations=['F2/F3 paired contrasts and predictive CV are separate required report components.',
            'World bootstraps preserve conditions; renderer/background graph sensitivities can have few clusters.',
            'No unique objective gold for unverified P4; no equivalence conclusion without a prespecified margin.'])

def analyze_complete(bundle,rows,design,reps=2000):
    """All predeclared modules for one model; cross-model Holm is applied by collection."""
    from epistemic_benchmark.analysis.mechanisms import analyze as diagnostic_analysis
    from epistemic_benchmark.analysis.predictive import compare
    result=analyze(bundle,rows,reps)
    result['F2_F3_diagnostics']=diagnostic_analysis(bundle,rows,reps)
    result['predictive_comparison']=compare(bundle['worlds'],{r['request_id']:r for r in rows},design)
    result['limitations']=[v for v in result['limitations'] if not v.startswith('F2/F3 paired contrasts')]
    return result
