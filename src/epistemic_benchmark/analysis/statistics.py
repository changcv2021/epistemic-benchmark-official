"""World-clustered G1-X contrasts and preregistered parameter-free policies."""

import random

from collections import Counter, defaultdict

from statistics import mean

from epistemic_benchmark.utils.io import SEED, require

def estimate(records, world_to_cluster=None, reps=2000):
    """Input is a list of (world_id, value); aggregate within world before resampling."""
    grouped=defaultdict(list)
    for world,value in records:grouped[world].append(value)
    values={k:mean(v) for k,v in grouped.items()}
    if not values:return dict(estimate=None,ci95=None,worlds=0,clusters=0,observations=0)
    clusters=defaultdict(list)
    for w,v in values.items():clusters[world_to_cluster[w] if world_to_cluster else w].append(v)
    groups=list(clusters.values());rng=random.Random(SEED)
    samples=[]
    if len(groups)>=2:
        for _ in range(reps):
            sample=[v for g in rng.choices(groups,k=len(groups)) for v in g]
            samples.append(mean(sample))
        samples.sort()
    return dict(estimate=mean(values.values()),ci95=[samples[int(.025*reps)],samples[int(.975*reps)-1]] if samples else None,
        worlds=len(values),clusters=len(groups),observations=len(records),
        degenerate_bootstrap=bool(samples and samples[0]==samples[-1]),
        note='Empirical clustered interval; zero observed errors is not population zero; small development sample.')

def policy_predictions(c):
    reports=c['reports'];roots={r['root']:r for r in reports}
    def vote(rows,weights=None):
        counts=defaultdict(float)
        for r in rows:counts[r['state']]+=1 if weights is None else weights[r['source']]
        if not counts:return 'A'
        top=max(counts.values());winners=[s for s in ('A','B') if counts[s]==top]
        return winners[0] if len(winners)==1 else None
    h={s:sum(r['reported']==r['verified'] for r in c['history'] if r['source']==s) for s in ('O1','O2')}
    last='A' if not reports or c['initial_record']['presented_position']>c['later_records']['presented_position'] else reports[-1]['state']
    newest='A' if not reports or c['initial_record']['refers_to_time']>c['later_records']['refers_to_time'] else vote(roots.values())
    # Quality-only treats the trusted initial record as high quality; limited later records have lower rank.
    # At equal high quality, vote among initial and distinct roots, rather than inventing a tie preference.
    quality='A' if c['quality']=='limited' else vote([dict(state='A')]+list(roots.values()))
    return dict(last_target_text=last,newest_referred_event=newest,initial_fact='A',
        report_votes=vote(reports),root_votes=vote(roots.values()),history_weighted_root_votes=vote(roots.values(),h),quality_rank=quality)

def analyze(bundle, rows, reps=2000):
    index={r['request_id']:r for r in rows}
    require(len(index)==len(bundle['requests'])==1920,'Complete scoring denominator required')
    worlds=[w['world_id'] for w in bundle['worlds']]
    renderer={w['world_id']:w['renderer_id'] for w in bundle['worlds']}
    event={w['world_id']:w['event_graph_signature'] for w in bundle['worlds']}
    def stats(records):return {'world':estimate(records,reps=reps),'renderer_sensitivity':estimate(records,renderer,reps),
                               'event_graph_sensitivity':estimate(records,event,reps)}
    summaries={}
    for family,probe in sorted({(r['family'],r['probe_id']) for r in rows}):
        rr=[r for r in rows if r['family']==family and r['probe_id']==probe]
        gold=[r for r in rr if r['has_gold'] and r['status']=='completed']
        summaries[family+'.'+probe]=dict(planned=len(rr),states=dict(Counter(r['outcome_state'] for r in rr)),
            format_valid=stats([(r['world_id'],int(r['valid'])) for r in rr]),
            completed_gold_denominator=len(gold),correct=sum(bool(r['correct']) for r in gold),
            protocol_inclusive_accuracy=stats([(r['world_id'],int(bool(r['correct']))) for r in gold]),
            semantic_accuracy_valid_only=stats([(r['world_id'],int(bool(r['correct']))) for r in gold if r['valid']]))
    condition_tables={}
    for family,variant,probe in sorted({(r['family'],r['variant'],r['probe_id']) for r in rows}):
        rr=[r for r in rows if (r['family'],r['variant'],r['probe_id'])==(family,variant,probe)]
        condition_tables[f'{family}.{variant}.{probe}']=dict(planned=len(rr),completed=sum(r['status']=='completed' for r in rr),
            valid=sum(r['valid'] for r in rr),states=dict(Counter(r['outcome_state'] for r in rr)),
            semantic_answers=dict(Counter(str(r['semantic_answer']) for r in rr if r['valid'])),
            correct=sum(bool(r['correct']) for r in rr),has_gold=rr[0]['has_gold'],
            world_interval=estimate([(r['world_id'],int(bool(r['correct'])) if r['has_gold'] else int(r['semantic_answer']=='B'))
                for r in rr if (r['status']=='completed' if r['has_gold'] else r['valid'])],reps=reps))
    def paired(label, left, right, selector=None):
        records=[];flips=[];eligible=0;bounds=[]
        for w in worlds:
            a=index[w+'.'+left];b=index[w+'.'+right]
            if selector is not None and not selector(w):continue
            eligible+=1
            av=int(a['semantic_answer']=='B') if a['valid'] else None
            bv=int(b['semantic_answer']=='B') if b['valid'] else None
            if av is not None and bv is not None:
                records.append((w,bv-av));flips.append((w,int(av!=bv)))
            bounds.append(((bv if bv is not None else 0)-(av if av is not None else 1),
                           (bv if bv is not None else 1)-(av if av is not None else 0)))
        return dict(label=label,direction='right_minus_left_in_B_choice',planned_worlds=24,eligible_worlds=eligible,
            valid_pairs=len(records),effect=stats(records),flip_rate=stats(flips),
            all_eligible_missing_bounds=[mean(b[i] for b in bounds) for i in (0,1)] if bounds else None,
            selected_subset=selector is not None)
    contrasts={}
    for pattern in ('BB','AB'):
        for suffix in ('NONE','COUNT_APPEND','SHAM_APPEND'):
            key=f'HL_to_LH.{pattern}.{suffix}'
            contrasts[key]=paired(key,f'R.HL.{pattern}.{suffix}.P4',f'R.LH.{pattern}.{suffix}.P4')
        key=f'HL_to_LH.{pattern}.P3c_correct_pair_DESCRIPTIVE'
        contrasts[key]=paired(key,f'R.HL.{pattern}.NONE.P4',f'R.LH.{pattern}.NONE.P4',
            lambda w: all(index[f'{w}.R.{p}.{pattern}.NONE.P3c']['correct'] for p in ('HL','LH')))
        key=f'LL_to_HH.{pattern}'
        contrasts[key]=paired(key,f'R.LL.{pattern}.NONE.P4',f'R.HH.{pattern}.NONE.P4')
        for profile in ('HH','LL','HL','LH'):
            for left,right in [('NONE','COUNT_APPEND'),('NONE','SHAM_APPEND'),('SHAM_APPEND','COUNT_APPEND')]:
                key=f'{left}_to_{right}.{profile}.{pattern}'
                contrasts[key]=paired(key,f'R.{profile}.{pattern}.{left}.P4',f'R.{profile}.{pattern}.{right}.P4')
    for time in ('08:00','12:00'):
        key=f'text_order_at_{time}';contrasts[key]=paired(key,f'T.A_first.{time}.P4',f'T.B_first.{time}.P4')
    for order in ('A_first','B_first'):
        key=f'event_time_at_{order}';contrasts[key]=paired(key,f'T.{order}.08:00.P4',f'T.{order}.12:00.P4')
    t_interaction=[]
    for w in worlds:
        corners=[index[f'{w}.T.{order}.{time}.P4'] for time in ('08:00','12:00') for order in ('A_first','B_first')]
        if all(r['valid'] for r in corners):
            a,b,c,d=[int(r['semantic_answer']=='B') for r in corners]
            t_interaction.append((w,(d-c)-(b-a)))
    contrasts['text_order_x_event_time']=dict(planned_worlds=24,complete_worlds=len(t_interaction),effect=stats(t_interaction),
        definition='Text-order effect at 12:00 minus text-order effect at 08:00')
    for pattern in ('AA','BB'):
        key=f'option_order_{pattern}';contrasts[key]=paired(key,f'L.{pattern}.AB.P4',f'L.{pattern}.BA.P4')
    for a,b in ((0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(4,7)):
        key=f'C{a}_to_C{b}';contrasts[key]=paired(key,f'C.C{a}.P4',f'C.C{b}.P4')
    count_joint=[]
    for w in worlds:
        for profile in ('HH','LL','HL','LH'):
            for pattern in ('BB','AB'):
                rr=[index[f'{w}.R.{profile}.{pattern}.NONE.{p}'] for p in ('P3a','P3b')]
                if all(r['status']=='completed' for r in rr):count_joint.append((w,int(all(r['correct'] for r in rr))))
    strategies=defaultdict(list);ties=Counter();policy_planned=0
    for c in bundle['cases']:
        if c['family'] not in ('T','L','C'):continue
        policy_planned+=1;r=index[c['case_id']+'.P4']
        for name,prediction in policy_predictions(c).items():
            if prediction is None:ties[name]+=1
            elif r['valid']:strategies[name].append((r['world_id'],int(r['semantic_answer']==prediction)))
    return dict(status='analysis_of_observed_responses',planned=1920,worlds=24,bootstrap_repetitions=reps,
        summaries=summaries,condition_tables=condition_tables,contrasts=contrasts,joint_exact_count_accuracy=stats(count_joint),
        strategy_agreement={k:dict(planned_cases=policy_planned,policy_ties=ties[k],valid_scored_cases=len(v),agreement=stats(v)) for k,v in strategies.items()},
        limits=['Development only; no confirmatory 40/50 comparison on these new worlds.',
            'K/P3c-selected contrasts are descriptive; no shared-forward-pass knowledge inference.',
            'Ties in policy baselines abstain; fit summaries alone do not establish an internal policy.',
            'C0/C1 padding adds possible distraction; token residuals must accompany conclusions.'])
