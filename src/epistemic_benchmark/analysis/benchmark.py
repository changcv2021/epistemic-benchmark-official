"""Frozen multidimensional benchmark profiles; every bootstrap unit is a world."""

from collections import Counter,defaultdict

import numpy as np

from epistemic_benchmark.utils.benchmark import *

from epistemic_benchmark.analysis.interventions import bootstrap

from epistemic_benchmark.analysis.design import coefficients

def definitions():
    d={}
    for metric,task,conditions,field in [
        ('InitialStateAcc','InitialState',['C'+str(i) for i in range(1,9)],'correct'),
        ('SourceProvenanceJointAcc','SourceProvenance',['C'+str(i) for i in range(1,9)],'correct'),
        ('SourceAcc','SourceProvenance',['C'+str(i) for i in range(1,9)],'bindings'),
        ('IndependenceRecognitionAcc','SourceProvenance',['C'+str(i) for i in range(1,9)],'root_count'),
        ('QualityRecognitionAcc','SourceProvenance',['C'+str(i) for i in range(1,9)],'quality'),
        ('RelativeReliabilityAcc','RelativeReliability',['HH','LL','HL','LH'],'correct')]:
        d[metric]=dict(track='T1',kind='accuracy',field=field,weights={('T1',task,c):1/len(conditions) for c in conditions})
    for p in ('HH','LL','HL','LH'):d['RelativeReliabilityAcc_'+p]=dict(track='T1',kind='accuracy',field='correct',weights={('T1','RelativeReliability',p):1})
    d['ExactCountAcc']=dict(track='T1',kind='accuracy',field='correct',secondary=True,weights={('T1',t,p):1/8 for t in ('ExactCountO1','ExactCountO2') for p in ('HH','LL','HL','LH')})
    for name,w in coefficients().items():d['Delta_'+name]=dict(track='T2',kind='choice_contrast',weights={('T2','Factorial',c):v for c,v in w.items()})
    d['ReliabilitySwapEffect']=dict(track='T3',kind='choice_contrast',weights={('T3','ReliabilitySwap','HL'):-1,('T3','ReliabilitySwap','LH'):1})
    d['ReliabilitySwapEffect_P3cCorrect_DESCRIPTIVE']={**d['ReliabilitySwapEffect'],'selected':True}
    for name,weights in [
        ('TextOrderEffect',[-.5,.5,-.5,.5]),('EventTimeEffect',[-.5,-.5,.5,.5]),('TextOrder_x_EventTime',[1,-1,-1,1])]:
        cs=('A_first.08:00','B_first.08:00','A_first.12:00','B_first.12:00')
        d[name]=dict(track='T4',kind='choice_contrast',weights={('T4','TextTime',c):v for c,v in zip(cs,weights)})
    for time in ('08:00','12:00'):d['TextOrderEffect_at_'+time]=dict(track='T4',kind='choice_contrast',weights={('T4','TextTime','A_first.'+time):-1,('T4','TextTime','B_first.'+time):1})
    for name,a,b in [('RepetitionEffect','S1','S2'),('SpeakerMultiplicityEffect','S2','S3'),('IndependentEvidenceEffect','S3','S4')]:
        d[name]=dict(track='T4',kind='choice_contrast',weights={('T4','ReportStructure',a):-1,('T4','ReportStructure',b):1})
    for name,conditions in [('VerifiedAccuracy',['A','B']),('VerifiedAAcc',['A']),('VerifiedBAcc',['B'])]:
        d[name]=dict(track='T5',kind='accuracy',field='correct',weights={('T5','Verified',c):1/len(conditions) for c in conditions})
    return d

def vectors(worlds,rows):
    require(len(rows)==24000,'A complete model must have 24000 scored items')
    index={(r['world_id'],r['track_id'],r['task_id'],r['condition_id']):r for r in rows}
    require(len(index)==len(rows),'Duplicate benchmark cell');output={}
    for metric,definition in definitions().items():
        values=[];bounds=[];eligible=[];invalid=[];technical=[];counts=[]
        for w in worlds:
            wid=w['world_id'];keep=not definition.get('selected') or all(index[wid,'T1','RelativeReliability',p]['correct'] is True for p in ('HL','LH'))
            eligible.append(keep);terms=[];lo=hi=0;bad=tech=0
            for cell,weight in definition['weights'].items():
                r=index[(wid,*cell)];bad+=int(not r['valid']);tech+=int(r['status']!='completed')
                if definition['kind']=='accuracy':
                    field=definition['field']
                    if field=='correct':v=float(bool(r['correct']))
                    else:v=float(bool(r['valid'] and isinstance(r['semantic_answer'],dict) and r['semantic_answer'].get(field)==r['gold_answer'][field]))
                else:v=float(r['semantic_answer']=='B') if r['valid'] else None
                terms.append(None if v is None else weight*v)
                if v is None:lo+=min(weight,0);hi+=max(weight,0)
                else:lo+=weight*v;hi+=weight*v
            values.append(sum(terms) if keep and all(v is not None for v in terms) else np.nan)
            bounds.append((lo,hi));invalid.append(bad);technical.append(tech);counts.append(len(definition['weights']))
        output[metric]=dict(values=np.asarray(values),bounds=np.asarray(bounds),eligible=np.asarray(eligible),invalid=np.asarray(invalid),technical=np.asarray(technical),counts=np.asarray(counts))
    return output

def analyze(worlds,rows):
    definitions_=definitions();vv=vectors(worlds,rows);stats=[];coverage=[];byworld=[]
    groups=[(s,'subset',np.asarray([s=='all' or w['split']==s for w in worlds])) for s in ('core','structural','naturalistic','all')]
    for family in sorted({w['relation_family'] for w in worlds}):
        for split in ('core','all'):groups.append((split+':'+family,'relation_family',np.asarray([w['relation_family']==family and (split=='all' or w['split']==split) for w in worlds])))
    row_world=defaultdict(list)
    for r in rows:row_world[r['world_id']].append(r)
    for group,scope,mask in groups:
        if not mask.any():continue
        for metric,data in vv.items():
            eligible=mask & data['eligible'];valid=eligible & np.isfinite(data['values']);d=definitions_[metric]
            bounds=data['bounds'][eligible].mean(axis=0).tolist() if eligible.any() else None
            stats.append(dict(group=group,scope=scope,track_id=d['track'],metric=metric,planned_worlds=int(mask.sum()),eligible_worlds=int(eligible.sum()),
                planned_requests=int(data['counts'][mask].sum()),eligible_requests=int(data['counts'][eligible].sum()),invalid_requests=int(data['invalid'][eligible].sum()),
                technical_failures=int(data['technical'][eligible].sum()),missing_worlds=int(eligible.sum()-valid.sum()),all_eligible_missing_bounds=bounds,
                accuracy_denominator='all_planned_requests_failure_zero' if d['kind']=='accuracy' else None,
                descriptive_response_selected_subset=bool(d.get('selected')),secondary=bool(d.get('secondary')),
                **bootstrap(data['values'][valid],reps=5000)))
        if scope=='subset':
            ww=[w for w,keep in zip(worlds,mask) if keep]
            for track in ('all','T1','T2','T3','T4','T5'):
                rr=[r for w in ww for r in row_world[w['world_id']] if track=='all' or r['track_id']==track];rates=[]
                for w in ww:
                    selected=[r for r in row_world[w['world_id']] if track=='all' or r['track_id']==track]
                    rates.append(sum(r['valid'] for r in selected)/len(selected))
                coverage.append(dict(subset=group,track_id=track,planned=len(rr),completed=sum(r['status']=='completed' for r in rr),
                    technical_failures=sum(r['status']!='completed' for r in rr),valid_format=sum(r['valid'] for r in rr),invalid_format=sum(r['invalid_format'] for r in rr),
                    truncated=sum(r['truncated'] for r in rr),protocol_deviations=sum(r['protocol_violation'] for r in rr),states=dict(Counter(r['outcome_state'] for r in rr)),format_interval=bootstrap(rates,reps=5000)))
    for metric,data in vv.items():
        for i,w in enumerate(worlds):byworld.append(dict(world_id=w['world_id'],metric=metric,value=float(data['values'][i]) if np.isfinite(data['values'][i]) else None,eligible=bool(data['eligible'][i])))
    return dict(status='complete',worlds=500,requests=24000,bootstrap_repetitions=5000,numpy_version=np.__version__,statistics=stats,coverage=coverage,per_world=byworld,
        design_sha256=sha(ROOT/'configs/benchmark/design.json'),primary_subset='core',overall_score=None,notes='No request-level pseudo-replication. Inclusive truth accuracy; unverified invalid choices missing. P3c-selected effect is descriptive. InternVL uses Qwen3 language backbones; do not claim fully independent architectural families.')
