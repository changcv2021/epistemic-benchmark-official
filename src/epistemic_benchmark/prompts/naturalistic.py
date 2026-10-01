"""Controlled prose revisions of the 80 user-reviewed bases; never human-authored claims."""

import re

from collections import Counter

from epistemic_benchmark.utils.io import *

from epistemic_benchmark.prompts.factorial import validate

OPENINGS=(
    'Before handing over at the {setting}, the coordinator pulled together the paperwork on {target}. One field still needed checking: its {relation}. The two values in the file were {a} and {b}.',
    'The file on {target} reached the records desk at the {setting} with a practical question attached. For its {relation}, should the team enter {a} or {b}? The documents below were supplied for that review.',
    'At the {setting}, the incoming team was looking through the file for {target}. They were asked to compare {a} with {b} as its {relation}, using the material that accompanied the file.',
    'A coordinator at the {setting} was putting together a short update about {target}. The update needed one choice about its {relation}: {a} or {b}. The relevant entries had been collected in the same packet.',
    'The paperwork for {target} was open on the desk at the {setting}. Rather than fill in its {relation} immediately, the records clerk passed along the available entries; the alternatives being considered were {a} and {b}.',
    'At the {setting}, a handoff file asked the next reader to settle the {relation} of {target}. It listed two possibilities, {a} and {b}, and included the record extracts reproduced below.',
    'Someone preparing the records at the {setting} flagged the file for {target} for another reading. The unresolved entry was its {relation}, with {a} and {b} as the candidates. The supplied records follow.',
    'The team at the {setting} needed a short answer about the {relation} of {target}. The choice on the form was between {a} and {b}; the supporting material was attached for the reader to consider.',
)

def prose_frame(w,c,style):
    old=c['segments']['framing']
    if c.get('initial_only'):return old
    text=OPENINGS[style].format(setting=w['fixed_non_target_attributes']['case_setting'],target=w['target_entity'],
        relation=w['target_relation'],a=w['candidate_states']['A'],b=w['candidate_states']['B'])
    topic=w['target_entity']
    genre=w['discourse_format']
    heads={
        'third_person_narrative':text,
        'first_person_report':'From the handoff writer: I have put the available entries below so the next person can check the file.\n'+text,
        'two_person_dialogue':'Coordinator: Could you pull together the entries for '+topic+'?\nClerk: Yes. Here is the question with the attached records; I have not added an observation.\n'+text,
        'group_chat':'Handoff chat\nCoordinator: The file for '+topic+' needs a reading.\nRecords clerk: I am pasting the question and the supplied entries here. These messages from me only pass along the file.\n'+text,
        'email_thread':'Subject: '+topic+' — file for review\n\nHello team,\nThe question and record extracts are copied below for the handoff.\n'+text,
        'incident_report':'Record-review note\nFile: '+topic+'\n\n'+text,
        'timestamped_log':'Archive reading copy\nFile: '+topic+'\nThe times given inside the entries belong to the events and receipt of records, respectively.\n\n'+text,
        'handoff_notes':'For the incoming team\nFile to finish: '+topic+'\n\n'+text,
        'meeting_minutes':'Record-review meeting\nThe chair asked for the entries on '+topic+'. The clerk read the question and the extracts below; the meeting added no observation.\n\n'+text,
        'task_update_thread':'Open records task: '+topic+'\nCoordinator: The material needed for this item is attached below.\n\n'+text,
    }
    # Retain the exact caveats, fixed facts, background events and source identities.
    marker='This is a fictional case.' if c['family']=='F1' else 'All event and receipt times'
    require(marker in old,'Unrecognized framing: cannot safely retain protected framing tail')
    return heads[genre]+'\n\n'+old[old.index(marker):]

def prose_history(w,c,style):
    rows=c['history'];states=w['candidate_states']
    if not c['segments']['history']:return ''
    heading=(f'The file also contains earlier checks of the same kind of attribute ({w["target_relation"]}) in the same setting. '
        'There are eight fully verified, separate cases for each listed original source. All happened before today and concern earlier cases, not today\'s target. '
        'A history remains in the file even when that source\'s current record is not cited.\n')
    patterns=(
        '{episode}: {source} reported {claim}. The trusted check established {fact}.',
        'In {episode}, the report from {source} said {claim}; trusted verification put the value at {fact}.',
        '{episode} — claim recorded from {source}: {claim}; result of trusted verification: {fact}.',
        'For case {episode}, {source} gave {claim}. The verified outcome, established by the trusted check, was {fact}.',
        'Case {episode} lists {claim} as {source}\'s report and {fact} as the value found by trusted verification.',
        '{episode}: the claim supplied by {source} was {claim}, and the trusted verification found {fact}.',
        'The earlier entry {episode} records a report of {claim} from {source}; its completed trusted check found {fact}.',
        'For {episode}, compare {source}\'s reported value, {claim}, with the trusted verification result, {fact}.',
    )
    return heading+'\n'.join(patterns[style].format(episode=r['episode'],source=r['source'],claim=states[r['reported']],fact=states[r['verified']]) for r in rows)

def prose_initial(w,c,style):
    if c.get('initial_only'):return c['segments']['initial']
    topic=f'the {w["target_relation"]} of {w["target_entity"]}';a=w['candidate_states']['A']
    patterns=(
        'The first trusted record describes 10:00 today and was available at 10:00. It gives {a} for {topic}.',
        'At 10:00, the team had a trusted record for that same time. According to that record, {topic} was {a} at 10:00 today.',
        'A trusted entry was available at 10:00 today: at 10:00, {topic} was {a}.',
        'The initial entry is a trusted record, available at 10:00 and describing 10:00 today. The value it gives for {topic} is {a}.',
        'For the initial record, both the time described and the time it became available are 10:00 today. This trusted record states that {topic} was {a}.',
        'The reader was supplied at 10:00 with a trusted record of the state at 10:00 today. Its entry for {topic} is {a}.',
        'The trusted initial record was made available at 10:00 today. Looking specifically at 10:00, it records {a} as {topic}.',
        'The initial paperwork includes a trusted record that arrived at 10:00 today and refers to 10:00. In that record, {topic} is given as {a}.',
    )
    return section(w,'Initial record',patterns[style].format(topic=topic,a=a))

def section(w,name,text):
    genre=w['discourse_format']
    prefixes={'third_person_narrative':name+':','first_person_report':'I have copied the '+name.lower()+' here:',
        'two_person_dialogue':'Clerk, reading the '+name.lower()+':','group_chat':'Records clerk — '+name+':',
        'email_thread':'Attached extract: '+name,'incident_report':name,'timestamped_log':'['+name+']',
        'handoff_notes':name+' for the next reader:','meeting_minutes':'The clerk read the '+name.lower()+':',
        'task_update_thread':'Attached to this task: '+name}
    return prefixes[genre]+'\n'+text

def report_body(c):
    text=c['segments']['reports']
    if not text:return ''
    anchor=re.search(r'Record e\d+ is an observation by O\d+ referring to',text) if c['family']=='F1' else re.search(r'Received at 13:00\.',text)
    if anchor:return text[anchor.start():]
    require(c.get('c_variant')==0,'Missing record body outside the zero-report control')
    return ''

def prose_reports(w,c,style):
    if c.get('initial_only'):return c['segments']['reports']
    body=report_body(c)
    if not body:return section(w,'Later entries','No later source report is included in this packet.')
    # Preserve every evidence statement verbatim: styles change the administrative presentation only.
    bridges=('The following entries were included in the packet.','Here are the entries as copied into the file.',
        'The file contains the following record extracts.','These entries accompany the initial record.',
        'The copied material reads as follows.','The remaining evidence entries are reproduced here.',
        'The reader has the following source material.','Below is the source material supplied with the file.')
    return section(w,'Later entries',bridges[style]+'\n'+body)

def transform_case(w,c,style):
    if c.get('initial_only'):return c
    c['segments']={**c['segments'],'framing':prose_frame(w,c,style),'history':prose_history(w,c,style),
        'initial':prose_initial(w,c,style),'reports':prose_reports(w,c,style)}
    order=c.get('segment_order',list(c['segments']))
    c['context']='\n\n'.join(c['segments'][k] for k in order if c['segments'][k]);c['context_hash']=digest(c['context'])
    c['surface_revision']=dict(author='assistant',version='naturalistic_prose_v1',style=style,
        constraint='evidence_body_and_verification_verbatim; trusted_initial/history_paraphrases; segment order retained')
    return c

def semantic_digest(c):
    return digest({k:v for k,v in c.items() if k not in ('segments','context','context_hash','surface_revision','padding')})
