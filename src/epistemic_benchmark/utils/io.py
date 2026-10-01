"""Portable paths and deterministic serialization for the public artifact."""
import gzip
import hashlib
import json
import os
import socket
from pathlib import Path

ROOT = Path(os.environ.get('EPI_ROOT', Path(__file__).resolve().parents[3])).resolve()
PROJECT = PHASE = ROOT
SOURCE = ROOT / 'configs' / 'data'
SLATE = ROOT / 'outputs'
SEED = 20260929


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compute_only():
    """Allow workstations; reject known login hosts without pretending to migrate."""
    require(not socket.gethostname().split('.')[0].lower().startswith('login'),
            'Run substantial work on a workstation or a scheduler compute node.')


def open_text(path, mode='rt'):
    path = Path(path)
    return gzip.open(path, mode, encoding='utf-8') if path.suffix == '.gz' else path.open(mode.replace('t', ''), encoding='utf-8')


def read(path):
    with open_text(path) as stream:
        return json.load(stream)


def iter_lines(path):
    with open_text(path) as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def lines(path):
    return list(iter_lines(path))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open_text(path, 'wt') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')


def write_lines(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open_text(path, 'wt') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def text_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def load_bundle(study, root=ROOT, include_cases=False):
    root = Path(root)
    folder = root / 'data' / study
    bundle = {'worlds': lines(root / 'data' / 'worlds.jsonl.gz')}
    for name in ('requests', 'manifests', 'labels'):
        bundle[name] = lines(folder / (name + '.jsonl.gz'))
    if include_cases:
        for name in ('cases', 'reuse'):
            p = folder / (name + '.jsonl.gz')
            if p.exists():
                bundle[name] = lines(p)
    return bundle
