"""Pre-inference deterministic length matching using complete unrelated sentences."""

from epistemic_benchmark.utils.io import digest, require

from epistemic_benchmark.prompts.diagnostics import wrap

SENTENCES=(
 'An unrelated visitor leaflet describes the building entrance and the public notice board.',
 'The leaflet lists a reception desk, a coat stand, and a place for blank feedback forms.',
 'Its layout uses a title line followed by ordinary paragraphs about visitor facilities.',
 'These administrative details contain no observation or report about the target attribute.',
 'A paragraph explains that visitors may leave general comments on blank sheets beside the entrance.',
 'Another paragraph describes the illustrated map printed on the inside cover of the visitor leaflet.',
 'The map includes a drawing of the entrance and a symbol for the reception desk.',
 'The reverse side contains general information about keeping the shared notice board tidy.',
 'The leaflet uses ordinary dark lettering on plain paper with an unmarked outer margin.',
 'Readers can find a short description of the public seating area near the end of the leaflet.',
 'The final paragraph describes where blank visitor feedback sheets can be found.',
 'The cover has a plain heading.',
 'A footer follows the main text.',
 'The outer margin is blank.',
 'The paper is plain.',
 'A heading appears.',
 'A footer follows.',
)

def pad_controls(bundle,tokenizer,profile):
    from epistemic_benchmark.backends.tokenization import chat_input_token_count
    requests={r['request_id']:r for r in bundle['requests']}
    manifests={m['request_id']:m for m in bundle['manifests']}
    cases={c['case_id']:c for c in bundle['cases']}
    audit=[]
    def count(messages):return chat_input_token_count(tokenizer,messages,profile['chat_template_kwargs'])
    for w in bundle['worlds']:
        wid=w['world_id'];target=count(requests[f'{wid}.C.C4.P4']['messages'])
        for variant in ('C0','C1'):
            c=cases[f'{wid}.C.{variant}'];old=c['context'];base=requests[c['case_id']+'.P4']['messages']
            selected=[];available=list(SENTENCES)
            def render(sentences):
                seg={**c['segments'],'filler':wrap(w,'unrelated leaflet',' '.join(sentences)) if sentences else ''}
                return '\n\n'.join(seg[k] for k in c['segment_order'] if seg[k])
            def tokens(text):return count([base[0],{'role':'user','content':base[1]['content'].replace(old,text,1)}])
            best=render([]);best_n=tokens(best)
            while available:
                trials=[(abs(tokens(render(selected+[s]))-target),j,s) for j,s in enumerate(available)]
                delta,j,s=min(trials)
                if delta>=abs(best_n-target):break
                selected.append(s);available.pop(j);best=render(selected);best_n=tokens(best)
                if delta<=2:break
            require(abs(best_n-target)<=8,'Unable to match complete-sentence control filler within 8 tokens')
            c['segments']['filler']=wrap(w,'unrelated leaflet',' '.join(selected));c['context']=best;c['context_hash']=digest(best)
            c['padding']={'method':'complete_unrelated_sentences_greedy_v1','reference':'C4','primary_tokenizer':'Qwen/Qwen3.5-4B','residual':best_n-target}
            for probe in ('P4','CHECK'):
                rid=c['case_id']+'.'+probe;r=requests[rid];m=manifests[rid]
                r['messages'][1]['content']=r['messages'][1]['content'].replace(old,best,1)
                m['context_hash']=c['context_hash'];m['input_hash']=digest(r['messages'])
            audit.append(dict(world_id=wid,variant=variant,reference_tokens=target,matched_tokens=best_n,residual=best_n-target))
    return audit
