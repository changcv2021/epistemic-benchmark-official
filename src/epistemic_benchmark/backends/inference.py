"""Portable sequential adapter; each call gets exactly one system/user branch."""
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

from ..utils.io import digest, iter_lines, read, require, write
from .providers import call, decode, payload


def build_payload(entry, messages, profile):
    require([m['role'] for m in messages] == ['system', 'user'], 'Each request must use an independent context')
    if entry['provider'] == 'vllm':
        fields = ('temperature', 'top_p', 'top_k', 'presence_penalty', 'frequency_penalty', 'repetition_penalty', 'max_tokens', 'seed', 'chat_template_kwargs')
        return dict(model=entry['model_id'], messages=messages, stream=False, n=1, **{k: profile[k] for k in fields})
    return payload(entry, messages)


def run(root, study, config, output, limit=None):
    require(limit is None or limit > 0, 'Limit must be positive')
    require(config['provider'] in ('vllm', 'openai_compatible', 'openai_responses', 'anthropic'), 'Unknown provider')
    endpoint = os.environ[config.get('endpoint_env', 'EPI_API_BASE')].rstrip('/')
    parsed = urlsplit(endpoint)
    require(not parsed.username and not parsed.password and not parsed.query and not parsed.fragment, 'Credentials belong in environment variables')
    require(parsed.scheme == 'https' or parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost', '::1'), 'Use HTTPS or a local inference server')
    key = os.environ.get(config.get('api_key_env', 'EPI_API_KEY'), '')
    require(bool(key) or config['provider'] == 'vllm', 'Missing API key environment variable')
    entry = dict(config, endpoint=endpoint, key=key or 'EMPTY')
    profile = read(root / 'configs/models/open_profile.json')
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'run.json', dict(study=study, model_id=entry['model_id'], provider=entry['provider'], smoke_limit=limit,
                                  profile=profile if entry['provider'] == 'vllm' else 'provider_native', independent_contexts=True))
    count = 0
    with (output / 'attempts.jsonl').open('x', encoding='utf-8') as stream:
        for request in iter_lines(root / 'data' / study / 'requests.jsonl.gz'):
            if limit is not None and count >= limit:
                break
            body = build_payload(entry, request['messages'], profile)
            for number in range(1, 4):
                if number > 1:
                    time.sleep((1, 4)[number - 2])
                response = call(entry, body, timeout=profile['timeout_seconds'] if entry['provider'] == 'vllm' else 180)
                decoded = decode(entry, response)
                retryable = response['transport_error'] is not None or response['http_status'] in (408, 429, 500, 502, 503, 504) or response['http_status'] == 200 and decoded is None
                terminal = decoded is not None or not retryable or number == 3
                actual = (decoded or {}).get('response_model') or ''
                violations = [] if decoded is None or actual == entry['model_id'] or actual.startswith(entry['model_id'] + '-') else ['response_model_mismatch']
                row = dict(request_id=request['request_id'], attempt=number, input_hash=digest(request['messages']), payload_hash=digest(body),
                           terminal=terminal, retryable=retryable, status='completed' if decoded else 'technical_error', decoded=decoded,
                           http_status=response['http_status'], runtime_violations=violations)
                stream.write(json.dumps(row, ensure_ascii=False) + '\n')
                stream.flush()
                if terminal:
                    break
            require(response['http_status'] not in (400, 401, 403, 404), 'API configuration error; remaining requests suspended')
            count += 1
    write(output / 'completion.json', dict(requests=count, engineering_smoke=limit is not None))
