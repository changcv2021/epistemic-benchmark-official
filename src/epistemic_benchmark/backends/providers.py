import json
import urllib.request
import urllib.error
from ..utils.io import require

def payload(entry,messages):
    # Model and benchmark messages are the only substitutions in the examples.
    if entry['provider']=='anthropic':
        return dict(model=entry['model_id'],system=messages[0]['content'],messages=messages[1:],max_tokens=1024)
    if entry['provider']=='openai_responses':return dict(model=entry['model_id'],input=messages)
    return dict(model=entry['model_id'],messages=messages)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Credential-bearing API redirects are disabled')

def call(entry,body,timeout=120):
    endpoint=entry['endpoint']+('/v1/messages' if entry['provider']=='anthropic' else '/responses' if entry['provider']=='openai_responses' else '/chat/completions')
    headers={'Content-Type':'application/json'}
    if entry['provider']=='anthropic':headers.update({'x-api-key':entry['key'],'anthropic-version':'2023-06-01'})
    else:headers['Authorization']='Bearer '+entry['key']
    req=urllib.request.Request(endpoint,data=json.dumps(body).encode(),headers=headers,method='POST')
    opener=urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req,timeout=timeout) as response:status=response.status;raw=response.read(4*1024*1024).decode();response_headers={k:v for k,v in response.headers.items() if k.lower() in ('x-request-id','request-id','retry-after','x-ms-region')}
        return dict(http_status=status,raw_body=raw.replace(entry['key'],'[REDACTED]'),transport_error=None,response_headers=response_headers)
    except urllib.error.HTTPError as e:
        return dict(http_status=e.code,raw_body=e.read(1024*1024).decode(errors='replace').replace(entry['key'],'[REDACTED]'),transport_error=None,response_headers={})
    except (urllib.error.URLError,TimeoutError,ConnectionError,OSError) as e:
        return dict(http_status=None,raw_body=None,transport_error=(type(e).__name__+': '+str(e)).replace(entry['key'],'[REDACTED]'),response_headers={})

def decode(entry,response):
    if response['http_status']!=200:return None
    try:
        raw=json.loads(response['raw_body'])
        if entry['provider']=='openai_responses':
            content=''.join(b.get('text','') for item in raw.get('output',[]) if item.get('type')=='message' for b in item.get('content',[]) if b.get('type')=='output_text')
            u=raw.get('usage') or {};reasoning=[item for item in raw.get('output',[]) if item.get('type')=='reasoning']
            return dict(content=content,finish_reason='stop' if raw.get('status')=='completed' else 'length' if (raw.get('incomplete_details') or {}).get('reason')=='max_output_tokens' else raw.get('status'),
                reasoning_content=reasoning or None,response_model=raw.get('model'),usage=dict(prompt_tokens=u.get('input_tokens'),completion_tokens=u.get('output_tokens')),
                provider_usage=u,response_id=raw.get('id'))
        if entry['provider']=='anthropic':
            blocks=raw['content'];texts=[b['text'] for b in blocks if b['type']=='text'];reasoning=[b for b in blocks if b['type'] in ('thinking','redacted_thinking')];u=raw.get('usage',{})
            return dict(content=''.join(texts),finish_reason='stop' if raw['stop_reason']=='end_turn' else 'length' if raw['stop_reason']=='max_tokens' else raw['stop_reason'],
                reasoning_content=reasoning or None,response_model=raw.get('model'),usage=dict(prompt_tokens=u.get('input_tokens'),completion_tokens=u.get('output_tokens')),provider_usage=u)
        c=raw['choices'];require(len(c)==1,'Unexpected number of API responses');message=c[0]['message']
        return dict(content=message.get('content'),finish_reason=c[0]['finish_reason'],reasoning_content=message.get('reasoning_content') or message.get('reasoning'),
            response_model=raw.get('model'),usage=raw.get('usage'),system_fingerprint=raw.get('system_fingerprint'))
    except (ValueError,KeyError,TypeError,IndexError):return None
