"""Dataset validation, export, independent inference, scoring and analysis."""
import argparse
import copy
import gzip
import json
import os
import shutil
from collections import Counter
from pathlib import Path

STUDIES = ('benchmark', 'diagnostics', 'interventions')


def validate(root, study):
    from .utils.io import digest, iter_lines, read, require, sha
    inventory = read(root / 'data' / 'manifest.json')
    for name, record in inventory['files'].items():
        if name == 'data/worlds.jsonl.gz' or name.startswith('data/' + study + '/'):
            require(sha(root / name) == record['sha256'], 'Dataset checksum mismatch: ' + name)
    worlds = list(iter_lines(root / 'data/worlds.jsonl.gz'))
    require(Counter(w['split'] for w in worlds) == dict(core=300, structural=120, naturalistic=80), 'World split mismatch')
    folder = root / 'data' / study
    manifests = {r['request_id']: r for r in iter_lines(folder / 'manifests.jsonl.gz')}
    seen = set()
    for request in iter_lines(folder / 'requests.jsonl.gz'):
        rid = request['request_id']
        require(rid not in seen and rid in manifests, 'Duplicate or unknown request')
        seen.add(rid)
        require([m['role'] for m in request['messages']] == ['system', 'user'], 'Contexts must be independent')
        require(digest(request['messages']) == manifests[rid]['input_hash'], 'Changed model-visible input')
    require(len(seen) == inventory['studies'][study]['requests_per_model'] and seen == set(manifests), 'Incomplete denominator')
    label_ids = set()
    for label in iter_lines(folder / 'labels.jsonl.gz'):
        rid = label['request_id']
        require(rid not in label_ids and rid in seen, 'Duplicate or unknown label')
        label_ids.add(rid)
        require(label['has_gold'] or label['gold_answer'] is None, 'Unverified choice must not have objective gold')
    require(label_ids == seen, 'Incomplete labels')
    return dict(study=study, worlds=len(worlds), requests=len(seen), status='passed')


def score(study, bundle, attempts, native_api=False):
    from .evaluation.scoring import score as base_score
    from .evaluation.diagnostics import score as diagnostic_score
    if native_api:
        attempts = copy.deepcopy(attempts)
        for row in attempts:
            if row.get('decoded'):
                row['decoded']['reasoning_content'] = None
    rows = diagnostic_score(bundle, attempts) if study == 'diagnostics' else base_score(bundle, attempts)
    meta = {r['request_id']: r for r in bundle['manifests']}
    labels = {r['request_id']: r for r in bundle['labels']}
    for row in rows:
        manifest = meta[row['request_id']]
        keys = ('track_id', 'task_id', 'condition_id', 'split', 'renderer_id') if study == 'benchmark' else ('intervention_id', 'task_family', 'task_id', 'split', 'renderer_id') if study == 'interventions' else ()
        row.update({k: manifest[k] for k in keys})
        if study == 'benchmark':
            row['gold_answer'] = labels[row['request_id']]['gold_answer']
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(os.environ.get('EPI_ROOT', Path(__file__).resolve().parents[2])))
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('validate', 'export', 'score', 'analyze', 'run'):
        sub = commands.add_parser(command)
        sub.add_argument('--study', choices=STUDIES, required=True)
        if command != 'validate':
            sub.add_argument('--output', type=Path, required=True)
        if command == 'export':
            sub.add_argument('--world', help='Optional world ID; the full set is exported by default')
        if command == 'score':
            sub.add_argument('--attempts', type=Path, required=True)
            sub.add_argument('--native-api', action='store_true', help='Use the prespecified provider-native reasoning policy')
        if command == 'analyze':
            sub.add_argument('--scores', type=Path, required=True)
        if command == 'run':
            sub.add_argument('--config', type=Path, required=True)
            sub.add_argument('--limit', type=int, help='Engineering smoke only; not a complete experiment')
    args = parser.parse_args()
    args.root = args.root.resolve()
    os.environ['EPI_ROOT'] = str(args.root)
    from .utils.io import compute_only, iter_lines, load_bundle, read, require, write
    compute_only()
    if args.command == 'validate':
        print(json.dumps(validate(args.root, args.study)))
        return
    require(not args.output.exists(), 'Choose a new output path; existing results are never overwritten')
    if args.command == 'export':
        from .utils.io import write_lines
        wanted = None
        if args.world:
            wanted = {r['request_id'] for r in iter_lines(args.root / 'data' / args.study / 'manifests.jsonl.gz') if r['world_id'] == args.world}
            require(bool(wanted), 'Unknown world ID')
        rows = (r for r in iter_lines(args.root / 'data' / args.study / 'requests.jsonl.gz') if wanted is None or r['request_id'] in wanted)
        write_lines(args.output, rows)
    elif args.command == 'run':
        from .backends.inference import run
        run(args.root, args.study, read(args.config), args.output, args.limit)
    elif args.command == 'score':
        rows = score(args.study, load_bundle(args.study, args.root), list(iter_lines(args.attempts)), args.native_api)
        write(args.output, rows)
    else:
        bundle = load_bundle(args.study, args.root, include_cases=args.study == 'diagnostics')
        rows = read(args.scores)
        if args.study == 'benchmark':
            from .analysis.benchmark import analyze
            result = analyze(bundle['worlds'], rows)
        elif args.study == 'interventions':
            from .analysis.interventions import analyze
            result = analyze(bundle['worlds'], rows)
        else:
            from .analysis.diagnostics import analyze_complete
            result = analyze_complete(bundle, rows, read(args.root / 'configs/diagnostics/design.json'), reps=2000)
        write(args.output, result)
    print(json.dumps(dict(status='complete', command=args.command, output=str(args.output))))


if __name__ == '__main__':
    main()
