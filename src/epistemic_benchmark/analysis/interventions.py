"""Prespecified paired world bootstrap; invalid choices stay missing."""

from collections import Counter

import numpy as np

from epistemic_benchmark.utils.intervention import *

from epistemic_benchmark.analysis.design import coefficients

def definitions():
    d={'T1_'+name:({'T1.'+k:v for k,v in weights.items()},False) for name,weights in coefficients().items()}
    d['T2_R']=({'T2.HL':-1,'T2.LH':1},False)
    d['T3_Text']=({'T3.A_first.08:00':-.5,'T3.B_first.08:00':.5,'T3.A_first.12:00':-.5,'T3.B_first.12:00':.5},False)
    d['T3_Time']=({'T3.A_first.08:00':-.5,'T3.B_first.08:00':-.5,'T3.A_first.12:00':.5,'T3.B_first.12:00':.5},False)
    d['T3_Text_x_Time']=({'T3.A_first.08:00':1,'T3.B_first.08:00':-1,'T3.A_first.12:00':-1,'T3.B_first.12:00':1},False)
    for time in ('08:00','12:00'):d['T3_Text_at_'+time]=({'T3.A_first.'+time:-1,'T3.B_first.'+time:1},False)
    for order in ('A_first','B_first'):d['T3_Time_at_'+order]=({'T3.'+order+'.08:00':-1,'T3.'+order+'.12:00':1},False)
    for metric,a,b in [('Repetition','S1','S2'),('Speakers','S2','S3'),('Lineage','S3','S4')]:d['T4_'+metric]=({'T4.'+a:-1,'T4.'+b:1},False)
    for inclusive in (True,False):d['T5_Verified_'+('inclusive' if inclusive else 'valid_pair')]=({'T5.A':.5,'T5.B':.5},inclusive)
    return d

def bootstrap(a,b=None,absolute=False,groups=None,reps=5000):
    a=np.asarray(a,dtype=float);b=None if b is None else np.asarray(b,dtype=float)
    require(np.isfinite(a).all() and (b is None or np.isfinite(b).all()),'Bootstrap received invalid values')
    def statistic(x,y=None):
        x=np.mean(x,axis=-1);y=None if y is None else np.mean(y,axis=-1)
        if absolute:x=np.abs(x);y=None if y is None else np.abs(y)
        return x if y is None else x-y
    center=float(statistic(a,b)) if len(a) else None
    result=dict(estimate=center,ci95=None,valid_worlds=len(a),clusters=len(a) if groups is None else len(set(groups)),
        bootstrap_repetitions=reps,centered_bootstrap_p=None,degenerate_bootstrap=False)
    if len(a)<2 or result['clusters']<2:return result
    rng=np.random.default_rng(SEED)
    if groups is None:
        # Bounded batches cap memory while preserving one shared draw for both conditions.
        samples=[]
        for start in range(0,reps,250):
            idx=rng.integers(0,len(a),size=(min(250,reps-start),len(a)))
            samples.extend(statistic(a[idx],None if b is None else b[idx]).tolist())
    else:
        keys=list(dict.fromkeys(groups));blocks=[np.flatnonzero(np.asarray(groups)==k) for k in keys];samples=[]
        for _ in range(reps):
            idx=np.concatenate([blocks[j] for j in rng.integers(0,len(blocks),len(blocks))])
            samples.append(float(statistic(a[idx],None if b is None else b[idx])))
    samples=np.sort(np.asarray(samples));result.update(ci95=[float(samples[int(.025*reps)]),float(samples[int(.975*reps)-1])],
        centered_bootstrap_p=float((1+np.sum(np.abs(samples-center)>=abs(center)-1e-14))/(reps+1)),
        degenerate_bootstrap=bool(samples[0]==samples[-1]))
    return result

def vectors(worlds,rows):
    index={(r['world_id'],r['intervention_id'],r['task_family']+'.'+r['task_id']):r for r in rows}
    require(len(index)==len(rows)==50000,'Incomplete or repeated scoring denominator')
    result={};bounds={};missing={}
    valid_counts=Counter();total_counts=Counter()
    for r in rows:
        key=(r['world_id'],r['intervention_id']);valid_counts[key]+=int(r['valid']);total_counts[key]+=1
    defs=definitions()
    for condition in CONDITIONS:
        for metric,(weights,inclusive) in defs.items():
            values=[];limits=[];states=Counter()
            for w in worlds:
                terms=[];lo=hi=0.
                for task,weight in weights.items():
                    r=index[w['world_id'],condition,task];states[r['outcome_state']]+=1
                    value=(float(bool(r['correct'])) if inclusive else float(bool(r['correct'])) if r['valid'] and task.startswith('T5.') else
                        float(r['semantic_answer']=='B') if r['valid'] else None)
                    terms.append(None if value is None else weight*value)
                    if value is None:lo+=min(0.,weight);hi+=max(0.,weight)
                    else:lo+=weight*value;hi+=weight*value
                values.append(np.nan if any(v is None for v in terms) else sum(terms));limits.append((lo,hi))
            result[condition,metric]=np.asarray(values);bounds[condition,metric]=np.asarray(limits);missing[condition,metric]=dict(states)
        validity=[]
        for w in worlds:
            key=(w['world_id'],condition)
            require(total_counts[key]==20,'Within-world request count changed');validity.append(valid_counts[key]/20)
        result[condition,'Format_validity']=np.asarray(validity);bounds[condition,'Format_validity']=np.column_stack([validity,validity])
    return result,bounds

def analyze(worlds,rows):
    plan=read(ROOT/'configs/interventions/analysis_plan.json');reps=plan['bootstrap_repetitions'];require(reps>=5000,'Too few world bootstrap replicates')
    values,bounds=vectors(worlds,rows)
    metrics=list(definitions())+['Format_validity'];profiles=[];comparisons=[];coverage=[];per_world=[]
    subset_masks={'all':np.ones(len(worlds),dtype=bool)}
    subset_masks.update({split:np.asarray([w['split']==split for w in worlds]) for split in ('core','structural','naturalistic')})
    extra_abs=['T2_R','T3_Text','T3_Text_at_08:00','T3_Text_at_12:00','T3_Time','T4_Repetition','T4_Lineage']
    renderer=np.asarray([w['renderer_id'] for w in worlds])
    for condition in CONDITIONS:
        for metric in metrics:
            for wi,w in enumerate(worlds):
                value=values[condition,metric][wi]
                per_world.append(dict(world_id=w['world_id'],intervention=condition,metric=metric,effect=float(value) if np.isfinite(value) else None))
    for subset,mask in subset_masks.items():
        world_ids={w['world_id'] for w,keep in zip(worlds,mask) if keep}
        for condition in CONDITIONS:
            rr=[r for r in rows if r['world_id'] in world_ids and r['intervention_id']==condition]
            coverage.append(dict(subset=subset,intervention=condition,planned=len(rr),technical_completed=sum(r['status']=='completed' for r in rr),
                valid=sum(r['valid'] for r in rr),states=dict(Counter(r['outcome_state'] for r in rr)),
                format_interval=bootstrap(values[condition,'Format_validity'][mask],reps=reps)))
            for metric in metrics:
                v=values[condition,metric];usable=mask & np.isfinite(v);limit=np.mean(bounds[condition,metric][mask],axis=0)
                profiles.append(dict(subset=subset,intervention=condition,metric=metric,planned_worlds=int(mask.sum()),
                    all_planned_missing_bounds=limit.tolist(),**bootstrap(v[usable],reps=reps)))
            for metric in extra_abs:
                v=values[condition,metric];usable=mask & np.isfinite(v)
                profiles.append(dict(subset=subset,intervention=condition,metric='abs_'+metric,planned_worlds=int(mask.sum()),**bootstrap(v[usable],absolute=True,reps=reps)))
        for left,right in plan['primary_comparisons']+plan['additional_comparisons']:
            for metric in metrics+['abs_'+m for m in extra_abs]:
                absolute=metric.startswith('abs_');base_metric=metric[4:] if absolute else metric
                a=values[left,base_metric];b=values[right,base_metric];usable=mask & np.isfinite(a) & np.isfinite(b)
                record=dict(subset=subset,comparison=left+'-'+right,metric=metric,planned_worlds=int(mask.sum()),
                    primary=(subset in plan['main_subsets'] and [left,right] in plan['primary_comparisons'] and metric in plan['primary_endpoints']),
                    **bootstrap(a[usable],b[usable],absolute=absolute,reps=reps))
                if not absolute:
                    lo=bounds[left,base_metric][:,0]-bounds[right,base_metric][:,1]
                    hi=bounds[left,base_metric][:,1]-bounds[right,base_metric][:,0]
                    record['all_planned_missing_bounds']=[float(np.mean(lo[mask])),float(np.mean(hi[mask]))]
                if record['primary']:record['renderer_sensitivity']=bootstrap(a[usable],b[usable],absolute=absolute,groups=renderer[usable].tolist(),reps=reps)
                comparisons.append(record)
    return dict(status='complete',worlds=500,planned_requests=50000,bootstrap_repetitions=reps,coverage=coverage,
        profiles=profiles,comparisons=comparisons,per_world_effects=per_world,
        analysis_plan_sha256=sha(ROOT/'configs/interventions/analysis_plan.json'),numpy_version=np.__version__,
        primary_Holm='Pending all three models; fixed 48-member family, including missing estimates.',
        caution='Intervals are conditional on usable paired worlds; include worst-case missingness bounds. No equivalence from crossing zero, no internal-state claim, no outcome-driven prompt tuning.')
