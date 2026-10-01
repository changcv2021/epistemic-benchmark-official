"""500 symbolic formal candidates. No model calls and no invented human review."""

import copy

from collections import Counter

from epistemic_benchmark.utils.io import *

from epistemic_benchmark.data.quotas import load_quotas, validate as validate_quotas

DOMAINS={
 'office':('shared office','staff work area','administrative team'),
 'university':('university teaching centre','seminar wing','teaching support team'),
 'school':('school resource centre','preparation room','school support team'),
 'library':('public library','cataloguing room','library operations team'),
 'community_center':('community centre','activity office','community programme team'),
 'research_lab':('fictional research training laboratory','training room','laboratory support team'),
 'manufacturing':('demonstration workshop','inspection office','production support team'),
 'warehouse':('warehouse','inventory office','warehouse operations team'),
 'it_operations':('fictional IT training centre','service room','IT support team'),
 'software_development':('software development studio','project office','software project team'),
 'retail':('retail shop','stock office','shop operations team'),
 'restaurant':('restaurant','staff preparation office','restaurant support team'),
 'hotel':('hotel','staff office','hotel operations team'),
 'travel':('travel service centre','dispatch office','travel operations team'),
 'shipping':('shipping depot','dispatch room','shipping operations team'),
 'construction':('construction training site','site office','site support team'),
 'facilities':('facilities service centre','maintenance office','facilities team'),
 'fleet':('vehicle fleet depot','service office','fleet support team'),
 'utilities':('utilities training facility','control practice room','utilities support team'),
 'agriculture':('agricultural teaching site','equipment office','farm support team'),
 'home':('shared household','home study','household planning group'),
 'sports_club':('sports club','club office','club support team'),
 'event_planning':('event planning office','event preparation room','event support team'),
 'media_production':('media production studio','production office','media support team'),
 'makerspace':('community makerspace','tool office','makerspace support team')}

VARIANTS={
 'location':[
 ('reference binder','storage location','upper cabinet','lower cabinet'),('portable label printer','storage location','packing bench','service shelf'),
 ('equipment case','storage location','checkout counter','return rack'),('spare adapter kit','storage location','tool drawer','supply tray'),
 ('map folder','storage location','document cabinet','reading desk'),('practice sample box','storage location','inspection shelf','staging rack'),
 ('reusable sign set','storage location','front cupboard','rear cupboard'),('inventory scanner','storage location','charging shelf','dispatch counter'),
 ('demonstration display','storage location','training table','display alcove'),('visitor card holder','storage location','reception desk','side cabinet')],
 'custody':[
 ('equipment key','designated custodian','Ari','Morgan'),('access token','designated custodian','Leena','Samir'),
 ('original register','designated custodian','Nora','Elias'),('reserve handset','designated custodian','Tessa','Jamal'),
 ('seal stamp','designated custodian','Remy','Anika'),('checkout card','designated custodian','Tobin','Mina'),
 ('demonstration camera','designated custodian','Idris','Wren'),('loan folder','designated custodian','Cleo','Arun'),
 ('storage keyring','designated custodian','Zara','Owen'),('signed receipt book','designated custodian','Nico','Esme')],
 'assignment':[
 ('inventory reconciliation task','responsible person','Ari','Morgan'),('visitor briefing task','responsible person','Leena','Samir'),
 ('equipment check task','responsible person','Nora','Elias'),('document revision task','responsible person','Tessa','Jamal'),
 ('room preparation task','responsible person','Remy','Anika'),('schedule confirmation task','responsible person','Tobin','Mina'),
 ('supply count task','responsible person','Idris','Wren'),('sign placement task','responsible person','Cleo','Arun'),
 ('handoff review task','responsible person','Zara','Owen'),('test recording task','responsible person','Nico','Esme')],
 'schedule':[
 ('orientation session','booked start time','09:00','10:00'),('equipment demonstration','booked start time','10:15','11:15'),
 ('planning meeting','booked start time','13:00','14:00'),('collection appointment','booked start time','15:30','16:30'),
 ('inspection visit','booked start time','08:30','09:30'),('practice workshop','booked start time','11:00','12:00'),
 ('visitor tour','booked start time','14:15','15:15'),('resource booking','booked start time','16:00','17:00'),
 ('training briefing','booked start time','09:45','10:45'),('handoff meeting','booked start time','12:30','13:30')],
 'state':[
 ('demonstration controller','operating mode','manual','automatic'),('practice display','display layout','compact','expanded'),
 ('test recorder','recording mode','continuous','event triggered'),('sample dispenser','dispensing mode','single item','batch'),
 ('practice terminal','interface language','English','Spanish'),('training dashboard','refresh mode','manual refresh','automatic refresh'),
 ('test printer','printing mode','single sided','double sided'),('demonstration light panel','display mode','steady','pulsed'),
 ('practice scanner','capture mode','single scan','continuous scan'),('sample label unit','label layout','portrait','landscape')],
 'quantity':[
 ('visitor card tray','number of available cards','6 cards','9 cards'),('supply box','number of available clips','12 clips','8 clips'),
 ('practice token tray','number of available tokens','5 tokens','7 tokens'),('checkout rack','number of available adapters','4 adapters','6 adapters'),
 ('sign storage case','number of available signs','3 signs','5 signs'),('form drawer','number of available forms','10 forms','14 forms'),
 ('sample folder box','number of available folders','8 folders','11 folders'),('tag dispenser','number of available tags','7 tags','4 tags'),
 ('training kit shelf','number of available kits','2 kits','4 kits'),('badge tray','number of available badges','9 badges','6 badges')],
 'version':[
 ('orientation document','active revision','revision amber','revision violet'),('checkout procedure','active revision','revision cedar','revision birch'),
 ('setup checklist','active revision','revision maple','revision willow'),('room map','active revision','revision north','revision south'),
 ('training handout','active revision','revision cobalt','revision copper'),('service template','active revision','revision dune','revision reef'),
 ('visitor instructions','active revision','revision lark','revision wren'),('test script','active revision','revision quartz','revision slate'),
 ('inventory guide','active revision','revision meadow','revision forest'),('handoff form','active revision','revision spring','revision autumn')],
 'permission':[
 ('practice account','access scope','read only','read and edit'),('training profile','access scope','view only','view and submit'),
 ('demonstration account','access scope','browse only','browse and annotate'),('sample user profile','access scope','open only','open and export'),
 ('test account','access scope','inspect only','inspect and approve'),('practice guest profile','access scope','view only','view and comment'),
 ('sandbox reviewer account','access scope','comment only','comment and edit'),('training operator profile','access scope','read only','read and schedule'),
 ('sample author account','access scope','draft only','draft and publish'),('demonstration member profile','access scope','search only','search and download')],
 'membership':[
 ('training participant','assigned group','silver group','copper group'),('support member','assigned group','north group','south group'),
 ('practice coordinator','assigned group','cedar group','birch group'),('volunteer','assigned group','morning group','afternoon group'),
 ('resource assistant','assigned group','amber group','violet group'),('workshop participant','assigned group','maple group','willow group'),
 ('programme member','assigned group','river group','hill group'),('event helper','assigned group','lark group','wren group'),
 ('session participant','assigned group','quartz group','slate group'),('demonstration volunteer','assigned group','meadow group','forest group')],
 'outcome':[
 ('practice submission','review disposition','accepted','revision requested'),('test batch','inspection disposition','passed','held for recheck'),
 ('sample request','processing disposition','cleared','pending review'),('demonstration entry','validation disposition','confirmed','correction requested'),
 ('training record','audit disposition','complete','follow-up required'),('mock application','screening disposition','eligible','further information required'),
 ('trial checklist','verification disposition','approved','returned for amendment'),('practice reservation','confirmation disposition','confirmed','waitlisted'),
 ('sample return','acceptance disposition','accepted','inspection required'),('demonstration report','review disposition','released','held for correction')],
 'priority':[
 ('equipment service request','queue priority','routine','urgent'),('document review request','queue priority','standard','expedited'),
 ('supply order','queue priority','normal','high'),('training booking request','queue priority','regular','priority'),
 ('visitor assistance request','queue priority','ordinary','accelerated'),('setup ticket','queue priority','low','medium'),
 ('handoff check request','queue priority','medium','high'),('test rerun request','queue priority','routine','time critical'),
 ('label replacement request','queue priority','standard','urgent'),('resource access request','queue priority','regular','expedited')],
 'routing':[
 ('electronic service packet','selected next destination','intake queue','review queue'),('sample delivery order','selected next destination','north desk','south desk'),
 ('training message','selected next destination','planning inbox','operations inbox'),('practice dispatch record','selected next destination','Desk 2','Desk 4'),
 ('support notification','selected next destination','local team inbox','central team inbox'),('demonstration transfer order','selected next destination','collection bay','inspection bay'),
 ('visitor enquiry packet','selected next destination','reception inbox','information inbox'),('resource request packet','selected next destination','supply queue','approval queue'),
 ('sample file transfer','selected next destination','active folder','review folder'),('test work order','selected next destination','east desk','west desk')]}

BACKGROUND_FAMILIES=('single_change','historical_return','temporary_intermediate','parallel_entity',
    'proposal_not_activation','planned_vs_effective','conditional_release','alias_binding','scope_copy','supersession_chain')

def background(variant):
    f=BACKGROUND_FAMILIES[variant]
    nodes=[{'id':'b0','type':'historical_start','entity':'target','day':-3}];edges=[]
    specifications={
      'single_change':[('b1','completed_change',{'state':'A','day':-1})],
      'historical_return':[('b1','past_state',{'state':'B','day':-2}),('b2','completed_return',{'state':'A','day':-1})],
      'temporary_intermediate':[('b1','temporary_state',{'state':'C','day':-2}),('b2','temporary_arrangement_ended',{'day':-1})],
      'parallel_entity':[('b1','separate_record',{'entity':'distractor','state':'B','day':-1})],
      'proposal_not_activation':[('b1','proposal',{'proposed_state':'B','day':-1}),('b2','archived_unactivated',{'day':-1})],
      'planned_vs_effective':[('b1','plan_issued',{'planned_state':'B','planned_effective_day':1,'day':-1})],
      'conditional_release':[('b1','conditional_policy',{'target_state':'B','trigger':'signed_release','trigger_status':'not_provided','day':-1})],
      'alias_binding':[('b1','alias_registered',{'alias':'archive_alias','referent':'target','day':-1})],
      'scope_copy':[('b1','copy_record',{'entity':'training_copy','scope':'copy_only','state':'B','day':-1})],
      'supersession_chain':[('b1','old_record',{'record_status':'superseded','state':'B','day':-2}),('b2','replacement_record',{'state':'A','day':-1})]}
    for node,kind,extra in specifications[f]:
        prev=nodes[-1]['id'];nodes.append(dict(id=node,type=kind,entity='target',**{k:v for k,v in extra.items() if k!='entity'}))
        if 'entity' in extra:nodes[-1]['entity']=extra['entity']
        edges.append([prev,node,'precedes'])
    return dict(family=f,nodes=nodes,edges=edges)

def evidence_structure(axis,variant,donor):
    n=2;chain=0;routes=[('M1','e1'),('M2','e2')];extra_edges=[];extra_nodes=[]
    if axis=='source_count':n=3+variant;routes=[(f'M{i}',f'e{i}') for i in range(1,n+1)]
    elif axis=='evidence_graph_topology':
        routes=[('M1','e1'),('M2','e1'),('M3','e2')]
        if variant:routes.append(('M4','e2'));chain=1
    elif axis=='dependency_pattern':
        chain=1
    elif axis=='update_chain_length':chain=2+variant
    elif axis=='role_configuration':
        if variant:routes=[('O2','e1'),('O1','e2')]
        else:routes=[('O1','e1'),('M2','e2')]
    nodes=[{'id':f'O{i}','type':'original_observer'} for i in range(1,n+1)]
    nodes += [{'id':f'e{i}','type':'observation_record','refers_to_time':'12:00'} for i in range(1,n+1)]
    nodes+=extra_nodes
    independent_edges=[[f'O{i}',f'e{i}','originates'] for i in range(1,n+1)]+extra_edges
    shared_edges=copy.deepcopy(independent_edges)
    for relay,root in routes:
        parent=root;shared_parent=f'e{donor}'
        for depth in range(chain):
            ident=f'{relay}_archive_{depth+1}'
            actor='common_records_clerk' if axis=='dependency_pattern' and variant else ident+'_clerk'
            nodes.append({'id':ident,'type':'faithful_archive_transfer','actor':actor})
            independent_edges.append([parent,ident,'copies']);shared_edges.append([shared_parent,ident,'copies'])
            parent=shared_parent=ident
        # An observer and a relay event by the same person are different graph nodes.
        # Reusing the actor node here would invent a causal cycle when people cross-relay.
        relay_node='relay_event_'+relay
        nodes.append({'id':relay_node,'type':'faithful_messenger','actor':relay})
        independent_edges.append([parent,relay_node,'cites']);shared_edges.append([shared_parent,relay_node,'cites'])
    return dict(nodes=nodes,distinct_edges=independent_edges,shared_edges=shared_edges,
        active_original_sources=n,final_messages=[{'speaker':r,'distinct_root':root,'shared_root':f'e{donor}'} for r,root in routes],
        archive_chain_length=chain,root_count_distinct=n,root_count_shared=1,
        note='Observer nodes can also relay a different record; originating a record and relaying it are separate roles.')

def build_worlds(slots):
    worlds=[];axis_index=Counter()
    for i,slot in enumerate(slots):
        r=slot['relation_family'];variant=int(slot['material_event_slot'].rsplit('_',1)[1])-1
        noun,attribute,a,b=VARIANTS[r][variant]
        if i%2:a,b=b,a
        setting,room,team=DOMAINS[slot['domain']]
        target=f'{noun} {r[:2].upper()}-{i+1:04}'
        fixed={'case_setting':setting,'reference_room':room,'responsible_organization':team}
        if r=='schedule':fixed.update(event_date='fictional day 6',venue=room)
        if r=='permission':fixed.update(system='fictional practice system',resource='designated training workspace')
        if r=='priority':fixed.update(request_contents=noun,recipient=team)
        if r=='routing':fixed.update(contents='the same practice information packet',dispatch_time='18:00')
        bg=background(variant);axis=slot.get('structural_axis');key=(r,axis)
        av=axis_index[key]%2;axis_index[key]+=1
        graph=evidence_structure(axis,av,1 if i%2==0 else 2)
        world=dict(world_id=f'F500W{i+1:04}',slot_id=slot['slot_id'],split=slot['split'],relation_family=r,
            domain=slot['domain'],discourse_format=slot['discourse_format'],target_entity=target,target_relation=attribute,
            candidate_states={'A':a,'B':b},fixed_non_target_attributes=fixed,material_event_variant=f'{r}.{BACKGROUND_FAMILIES[variant]}.{variant+1:02}',
            renderer_id=f"formal500.{r}.{slot['discourse_format']}",background_graph=bg,
            initial_record={'refers_to_time':'10:00','received_at':'10:00','state':'A','status':'trusted_assertion'},
            target_time='14:00',structural_axis=axis,structural_variant=av if axis else None,evidence_graph=graph,
            event_graph_signature=digest(bg),provenance_graph_signature=digest(graph),
            quality_operation=('photo_identifier','log_identifier','document_identifier','audio_identifier')[i%4],
            shared_root_donor='O1' if i%2==0 else 'O2',default_option_order='AB' if i%2==0 else 'BA',
            panels={k:slot[k] for k in ('in_F2','in_F3','in_F4')},verified_base_condition=slot['verified_base_condition'],
            review_status='pending',second_independent_review_required=slot['second_independent_review_required'],
            second_review_status='pending' if slot['second_independent_review_required'] else 'not_selected',
            human_written=False,authorship='assistant_authored_symbolic_candidate',
            naturalistic_language_status='pending_author_source_decision' if slot['split']=='naturalistic' else 'not_applicable',
            status='SYMBOLIC_CANDIDATE_NOT_FROZEN_FOR_MODEL_RUN',main_target_truth=None,
            protocol_compatibility_issues=[])
        # Existing frozen G1-R/P protocols assume two focal original roots. Flag this BEFORE model execution.
        if axis=='source_count' and any(world['panels'].values()):
            world['protocol_compatibility_issues'].append('Extra active roots require explicit focal-source definition or pre-result panel reselection; cannot silently reuse two-root G1 renderer.')
        worlds.append(world)
    return worlds

def validate(worlds,slots,q):
    validate_quotas(slots,q)
    require(len(worlds)==len({w['world_id'] for w in worlds})==500,'Formal unique worlds')
    require(Counter(w['split'] for w in worlds)==q['splits'],'World splits')
    require(len({w['target_entity'] for w in worlds})==500,'Duplicate target identity')
    require(all(w['main_target_truth'] is None and not w['human_written'] and w['review_status']=='pending' for w in worlds),'False truth/authorship/review')
    for relation in VARIANTS:
        rr=[w for w in worlds if w['relation_family']==relation]
        require(len({w['material_event_variant'] for w in rr})==10,'Insufficient actual material variants')
    require(max(Counter(w['material_event_variant'] for w in worlds).values())<=12,'Material repetition cap')
    require(max(Counter(w['renderer_id'] for w in worlds).values())<=12,'Renderer repetition cap')
    for w in worlds:
        graph=w['evidence_graph'];roots={r['distinct_root'] for r in graph['final_messages']}
        require(len(roots)==graph['root_count_distinct'] and len({r['shared_root'] for r in graph['final_messages']})==1,'Provenance root count')
        require(w['candidate_states']['A']!=w['candidate_states']['B'],'Identical states')
        require(w['event_graph_signature']==digest(w['background_graph']),'Event signature mismatch')
        nodes={n['id'] for n in graph['nodes']}
        require(len(nodes)==len(graph['nodes']),'Duplicate graph nodes')
        for edge_name in ('distinct_edges','shared_edges'):
            edges=graph[edge_name];require(all(a in nodes and b in nodes for a,b,_ in edges),'Dangling graph edge')
            indegree={n:0 for n in nodes};children={n:[] for n in nodes}
            for a,b,_ in edges:indegree[b]+=1;children[a].append(b)
            ready=[n for n,d in indegree.items() if d==0];visited=0
            while ready:
                n=ready.pop();visited+=1
                for child in children[n]:
                    indegree[child]-=1
                    if indegree[child]==0:ready.append(child)
            require(visited==len(nodes),'Cyclic provenance graph')
    issues=[{'world_id':w['world_id'],'issues':w['protocol_compatibility_issues']} for w in worlds if w['protocol_compatibility_issues']]
    return dict(status='SYMBOLIC_CANDIDATES_VALIDATED_WITH_OPEN_REVIEW_ITEMS',worlds=500,splits=dict(Counter(w['split'] for w in worlds)),
        actual_material_variants=len({w['material_event_variant'] for w in worlds}),actual_background_graph_signatures=len({w['event_graph_signature'] for w in worlds}),
        actual_provenance_graph_signatures=len({w['provenance_graph_signature'] for w in worlds}),
        graph_signature_note='Background signatures do not include relation names or entity names; provenance signatures preserve directed node roles. Counts are not numbers of distinct cognitive mechanisms.',
        structural_axes=dict(Counter(w['structural_axis'] for w in worlds if w['split']=='structural')),
        pending_human_reviews=500,pending_second_reviews=sum(w['second_independent_review_required'] for w in worlds),
        naturalistic_language_pending=80,protocol_compatibility_issues=issues,new_model_calls=0,model_ready=False)
