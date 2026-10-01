"""Outcome-blind cross-validation partitions and factorial contrast definitions."""

from collections import defaultdict,Counter

from itertools import combinations

from epistemic_benchmark.utils.io import *

from epistemic_benchmark.prompts.factorial import CONDITIONS

def coefficients():
    result={}
    for order in (1,2,3):
        for factors in combinations('RQI',order):
            weights={}
            for cid,(r,q,i) in CONDITIONS.items():
                signs={'R':1 if r=='HH' else -1,'Q':1 if q=='high' else -1,'I':1 if i=='distinct' else -1}
                value=1
                for f in factors:value*=signs[f]
                weights[cid]=value/(2**(3-order))
            result['_x_'.join(factors)]=weights
    return result

def folds(worlds):
    require(len({w['world_id'] for w in worlds})==len(worlds),'Repeated world in CV plan')
    strata=defaultdict(list)
    for w in worlds:strata[w['relation_family'],w['split']].append(w)
    world_map={};loads=Counter()
    for key,group in sorted(strata.items()):
        local=Counter()
        for w in sorted(group,key=lambda w:digest([SEED,'world-fold',w['world_id']])):
            fold=min(range(5),key=lambda f:(local[f],loads[f],digest([key,f])))
            world_map[w['world_id']]=fold;loads[fold]+=1;local[fold]+=1
    renderers=defaultdict(list)
    for w in worlds:renderers[w['renderer_id']].append(w)
    nfolds=min(5,len(renderers));renderer_map={};loads=Counter()
    for renderer,group in sorted(renderers.items(),key=lambda kv:(-len(kv[1]),digest([SEED,'renderer-fold',kv[0]]))):
        fold=min(range(nfolds),key=lambda f:(loads[f],f));loads[fold]+=len(group)
        for w in group:renderer_map[w['world_id']]=fold
    return dict(world_grouped={'folds':5,'world_to_fold':world_map},
        renderer_grouped={'folds':nfolds,'world_to_fold':renderer_map},seed=SEED,
        outcome_data_used=False,n_worlds=len(worlds),renderer_clusters=len(renderers))

def validate_folds(worlds,plan):
    for kind,data in ((k,plan[k]) for k in ('world_grouped','renderer_grouped')):
        require(set(data['world_to_fold'])=={w['world_id'] for w in worlds},'Incomplete CV assignment')
        require(set(data['world_to_fold'].values())==set(range(data['folds'])),'Empty/illegal fold')
        if kind=='renderer_grouped':
            assignments=defaultdict(set)
            for w in worlds:assignments[w['renderer_id']].add(data['world_to_fold'][w['world_id']])
            require(all(len(v)==1 for v in assignments.values()),'Renderer leakage across CV folds')
    require(not plan['outcome_data_used'],'Partitions must be outcome blind')
