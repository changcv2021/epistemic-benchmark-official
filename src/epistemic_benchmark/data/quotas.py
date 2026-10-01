"""Crossed planning slots, NOT generated or reviewed formal worlds."""

import random

from collections import Counter, defaultdict

from epistemic_benchmark.utils.io import SOURCE, PHASE, SEED, read, write, write_lines, require

def load_quotas():
    return read(PHASE / 'configs/data/world_quotas.json')

def base_counts(q):
    if 'verified_base_counts' in q:return q['verified_base_counts']
    require(q['formal_worlds']%8==0,'Explicit near-balanced base assignment required')
    return {f'C{i}':q['formal_worlds']//8 for i in range(1,9)}

def allocate(q=None, output=None):
    q = q or load_quotas()
    rng = random.Random(SEED)
    slots = []
    format_names=list(q['formats']);cursor=0
    for relation_index,relation in enumerate(q['relations']):
        n = relation['total']
        formats = [format_names[(cursor+i)%len(format_names)] for i in range(n)]
        cursor+=n
        rng.shuffle(formats)
        variants = [f'event_slot_{i % 10 + 1:02}' for i in range(n)]
        rng.shuffle(variants)
        i = 0
        for split in ('core', 'structural', 'naturalistic'):
            for j in range(relation[split]):
                structural_panel=None
                if split=='structural' and q.get('structural_axes'):
                    eligible=[a for a in q['structural_axes'] if a not in q.get('panel_excluded_structural_axes',[])]
                    if q.get('panel_excluded_structural_axes'):
                        selected_axes=[a for k,a in enumerate(eligible) if k!=relation_index%len(eligible)]
                        structural_panel=q['structural_axes'][j//2] in selected_axes and j%2==relation_index%2
                slots.append(dict(slot_id=f'FS{len(slots)+1:04}', relation_family=relation['id'],
                    split=split, discourse_format=formats[i], material_event_slot=variants[i],
                    renderer_slot=f"{relation['id']}.{formats[i]}",
                    in_F2=structural_panel if structural_panel is not None else j < q['formal_panels']['reliability']['per_relation'][split],
                    in_F3=structural_panel if structural_panel is not None else j < q['formal_panels']['policy']['per_relation'][split],
                    human_review='pending', human_written=False,
                    status='QUOTA_SLOT_ONLY_NOT_A_WORLD',
                    structural_axis=q.get('structural_axes',[None]*5)[j//2] if split=='structural' else None))
                i += 1
    domains = [d for d, n in q['domains'].items() for _ in range(n)]
    for attempt in range(1000):
        rng.shuffle(domains)
        rd, dr = defaultdict(set), defaultdict(set)
        for row, domain in zip(slots, domains):
            rd[row['relation_family']].add(domain)
            dr[domain].add(row['relation_family'])
        if min(map(len, rd.values())) >= 12 and min(map(len, dr.values())) >= 8:
            break
    else:
        raise ValueError('Crossed quotas infeasible for the bounded allocator')
    conditions = [cid for cid,n in base_counts(q).items() for _ in range(n)]
    rng.shuffle(conditions)
    # Twenty percent stratified by relation and split, rounding UP in each stratum.
    # Naturalistic rows all require independent authorship and semantic/language review too.
    second = set()
    for relation in q['relations']:
        for split in q['splits']:
            ids = [r['slot_id'] for r in slots if r['relation_family'] == relation['id'] and r['split'] == split]
            rng.shuffle(ids)
            second.update(ids[:(len(ids)+4)//5])
    for row, domain, condition in zip(slots, domains, conditions):
        row.update(domain=domain, verified_base_condition=condition, in_F4=row['in_F3'],
                   second_independent_review_required=row['slot_id'] in second,
                   semantic_domain_fit='pending_human_review')
    audit = validate(slots, q)
    output=output or PHASE/('data/planning_500' if q['formal_worlds']==500 else 'data/planning')
    write_lines(output/'formal_quota_slots.jsonl', slots)
    write(output/'quota_audit.json', audit)
    return audit

def validate(rows, q=None):
    q = q or load_quotas()
    require(len(rows) == len({r['slot_id'] for r in rows}) == q['formal_worlds'], 'Slot count')
    require(Counter(r['domain'] for r in rows) == q['domains'], 'Domain quotas')
    require(Counter(r['discourse_format'] for r in rows) == q['formats'], 'Format quotas')
    require(Counter(r['split'] for r in rows) == q['splits'], 'Split quotas')
    require(Counter(r['verified_base_condition'] for r in rows) == base_counts(q), 'Verified bases')
    if q.get('structural_axes'):
        require(Counter(r['structural_axis'] for r in rows if r['split']=='structural')=={a:24 for a in q['structural_axes']},'Structural axes')
        require(all(not r['in_F2'] for r in rows if r['structural_axis'] in q.get('panel_excluded_structural_axes',[])),'Incompatible structural panel member')
    rd, dr = {}, {}
    for rel in q['relations']:
        selected = [r for r in rows if r['relation_family'] == rel['id']]
        require(Counter(r['split'] for r in selected) == {s:rel[s] for s in q['splits']}, 'Relation/split quotas')
        rd[rel['id']] = len({r['domain'] for r in selected})
        require(len({r['material_event_slot'] for r in selected}) == 10, 'Event slots')
        require(len({r['discourse_format'] for r in selected}) == 10, 'Format confounding')
        for panel, field in [('reliability', 'in_F2'), ('policy', 'in_F3')]:
            require(Counter(r['split'] for r in selected if r[field]) == q['formal_panels'][panel]['per_relation'], 'Panel stratum')
    dr = {d:len({r['relation_family'] for r in rows if r['domain']==d}) for d in q['domains']}
    require(min(rd.values()) >= 12 and min(dr.values()) >= 8, 'Crossed coverage')
    require(all(not r['in_F3'] or r['in_F2'] for r in rows), 'Nested panels')
    require(all(r['in_F4']==r['in_F3'] for r in rows), 'Truth panel')
    mv = max(Counter((r['relation_family'], r['material_event_slot']) for r in rows).values())
    mr = max(Counter(r['renderer_slot'] for r in rows).values())
    require(mv <= 12 and mr <= 12, 'Template cap')
    return dict(status='ARITHMETIC_FEASIBLE_SEMANTIC_REVIEW_PENDING', worlds_generated=0,
        slots=q['formal_worlds'],splits=q['splits'],seed=SEED, domains_per_relation=rd, relations_per_domain=dr,
        max_per_relation_event_slot=mv, max_per_renderer_slot=mr,
        panels={'F2':sum(r['in_F2'] for r in rows),'F3':sum(r['in_F3'] for r in rows),'F4':sum(r['in_F4'] for r in rows)},
        second_review_slots=sum(r['second_independent_review_required'] for r in rows),verified_base_counts=base_counts(q),
        structural_axes=dict(Counter(r.get('structural_axis') for r in rows if r['split']=='structural')),
        note='Slots prove numeric feasibility only; no claims about actual event graphs, semantic suitability, or human authorship.')
