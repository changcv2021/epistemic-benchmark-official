"""Twenty-four NEW development cases. Assistant-authored, awaiting human review."""

from epistemic_benchmark.utils.io import digest

EXAMPLES = [
 ('location','library','atlas case L17','storage location','map cabinet','reading alcove',{'contents':'regional atlases','floor':'second floor'}),
 ('location','warehouse','scanner kit W24','storage location','inspection rack','dispatch shelf',{'owner':'warehouse service','kit_id':'W24'}),
 ('custody','makerspace','calibration key K11','designated custodian','Tarin','Nessa',{'storage_room':'tool room','key_id':'K11'}),
 ('custody','hotel','master binder H28','designated custodian','Oren','Lila',{'storage_room':'staff office','binder_id':'H28'}),
 ('assignment','software_development','test ticket S31','assigned owner','Vera','Colin',{'project':'Orchid','task':'run the interface checks'}),
 ('assignment','community_center','welcome desk shift C42','assigned owner','Iris','Malik',{'date':'fictional day 5','shift_time':'17:00 to 18:00'}),
 ('schedule','university','seminar U16','scheduled start time','15:00','16:00',{'room':'Room 201','event_date':'fictional day 5'}),
 ('schedule','fleet','inspection F23','scheduled start time','09:30','10:30',{'bay':'Bay 4','event_date':'fictional day 6'}),
 ('state','utilities','test panel P19','operating mode','manual','automatic',{'site':'training shed','device_id':'P19'}),
 ('state','home','display unit H36','display mode','compact','expanded',{'location':'study','device_id':'H36'}),
 ('quantity','retail','display tray R14','number of available sample packs','6 packs','9 packs',{'product':'empty demonstration packs','tray_id':'R14'}),
 ('quantity','restaurant','rack R27','number of available clean pitchers','8 pitchers','5 pitchers',{'pitcher_size':'one litre','rack_id':'R27'}),
 ('version','research_lab','training protocol L33','active revision','revision amber','revision violet',{'procedure':'mock calibration','scope':'training only'}),
 ('version','media_production','caption file M18','published revision','revision cedar','revision birch',{'language':'English','episode':'E18'}),
 ('permission','it_operations','account demo_52','access level','read only','read and edit',{'system':'fictional sandbox','resource':'practice folder'}),
 ('permission','school','practice account P26','access level','view only','view and submit',{'system':'fictional classroom simulator','resource':'practice board'}),
 ('membership','sports_club','member M47','assigned training group','silver group','copper group',{'sport':'indoor rowing','session_date':'fictional day 7'}),
 ('membership','event_planning','volunteer V22','assigned team','registration team','stage team',{'event':'fictional craft fair','shift_time':'15:00 to 17:00'}),
 ('outcome','manufacturing','trial batch B39','inspection disposition','accepted','held for recheck',{'product':'demonstration brackets','batch_id':'B39'}),
 ('outcome','construction','mock permit P43','review disposition','revision requested','accepted',{'site':'training plot','scope':'temporary model frame'}),
 ('priority','shipping','consignment S12','dispatch priority','standard','expedited',{'destination':'Depot 8','contents':'sample cartons'}),
 ('priority','office','service request O29','queue priority','urgent','routine',{'request':'replace a desk lamp','room':'Room 12'}),
 ('routing','agriculture','irrigation test line A38','selected outlet','north test bed','south test bed',{'fluid':'clean water','line_id':'A38'}),
 ('routing','travel','shuttle service T21','assigned terminal','Terminal 2','Terminal 4',{'departure_time':'18:00','service_date':'fictional day 5'}),
]

BACKGROUNDS = [
 ('single_stage', 'On the previous day, the item entered routine service. No intermediate state is described.',
  [{'kind':'enter_service','day':-1}]),
 ('historical_return', 'Two days earlier the target had the second listed state. A completed return to the first listed state was recorded yesterday. These are past events.',
  [{'kind':'state','state':'B','day':-2},{'kind':'return','from':'B','to':'A','day':-1}]),
 ('parallel_entity', 'A separate training item, unrelated to the target, was discussed yesterday. Its record concerns only that other item and gives no information about the target today.',
  [{'kind':'unrelated_record','entity':'distractor','day':-1}]),
 ('proposal_activation', 'Yesterday a draft proposed the second listed state for the target. The draft had not taken effect when it was archived. No later activation is stated as a fact.',
  [{'kind':'propose','state':'B','day':-1},{'kind':'archive_unactivated','day':-1}]),
 ('scope_separation', 'Yesterday a training copy of the target used the second listed state. The copy and the live target are separate; the training entry does not describe the live target.',
  [{'kind':'state','entity':'training_copy','scope':'training','state':'B','day':-1}]),
 ('conditional_trigger', 'Yesterday a rule allowed a change to the second listed state only after a signed release. The rule itself is not a release; no release is supplied as an established fact.',
  [{'kind':'conditional_rule','trigger':'signed_release','to':'B','day':-1}]),
 ('intermediate_history', 'Earlier this week the target used a third, temporary state. That temporary arrangement ended yesterday; it is not one of the two states being compared today.',
  [{'kind':'temporary_state','state':'C','day':-3},{'kind':'end_temporary','day':-1}]),
 ('alias_binding', 'Yesterday an archive index assigned a short label to the target. The label and the full target name refer to the same item, not two separate items.',
  [{'kind':'alias','entity':'target','alias':'archive_label','day':-1}]),
]

FORMATS = ('third_person_narrative','first_person_report','two_person_dialogue','group_chat','email_thread',
           'incident_report','timestamped_log','handoff_notes','meeting_minutes','task_update_thread')

NAMES = ('Mara','Felix','Sana','Jules','Priya','Evan','Dara','Noel','Mei','Rowan','Aya','Luca')

def build_worlds():
    worlds=[]
    for i, (relation,domain,entity,predicate,a,b,fixed) in enumerate(EXAMPLES):
        # Mirrored numerical/lexical candidate directions are explicit in the authored examples.
        family, background, graph = BACKGROUNDS[i % len(BACKGROUNDS)]
        fmt=FORMATS[(i*3+i//10)%10]
        world=dict(world_id=f'XD{i+1:04}', split='development_only', index=i,
            relation_family=relation,domain=domain,target_entity=entity,target_relation=predicate,
            candidate_states={'A':a,'B':b},fixed_non_target_attributes=fixed,
            discourse_format=fmt,renderer_id=f'dev_v1.{fmt}',
            background_family=family,background_text=background,background_graph=graph,
            initial_record={'refers_to_time':'10:00','received_at':'10:00','state':'A','status':'trusted_assertion'},
            target_time='14:00', quality_operation=('photo_identifier','log_identifier','document_identifier','audio_identifier')[i%4],
            source_names={'O1':NAMES[i%12],'O2':NAMES[(i+5)%12],'M1':'Relay One','M2':'Relay Two'},
            shared_root_donor='O1' if i%2==0 else 'O2', default_option_order='AB' if i%2==0 else 'BA',
            review_status='pending',human_written=False,
            authorship='assistant_authored_templates_no_external_generation_calls',
            main_target_truth=None,formal_eligible=False)
        world['event_graph_signature']=digest({'background':graph,'initial':{'time':'10:00','state':'A'},'target_time':'14:00'})
        worlds.append(world)
    return worlds
