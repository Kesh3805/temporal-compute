"""Read-only GitHub PR review snapshot; no patches, replies, resolution or merge."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlparse

BOT = 'coderabbitai[bot]'
ROOT = Path(__file__).resolve().parents[1]
QUERY = '''query($owner:String!,$name:String!,$number:Int!,$cursor:String) {
 repository(owner:$owner,name:$name) { pullRequest(number:$number) {
 reviewThreads(first:100,after:$cursor) { pageInfo {hasNextPage endCursor}
 nodes { id isResolved isOutdated comments(first:1) {nodes {author {login} body url}} }
 } } } }'''


def gh(*args):
    result = subprocess.run(['gh', *args], capture_output=True, text=True,
                            encoding='utf-8', timeout=60, check=True)
    return json.loads(result.stdout)


def pages(endpoint):
    rows = []
    for page in range(1, 101):
        value = gh('api', f'{endpoint}{"&" if "?" in endpoint else "?"}per_page=100&page={page}')
        items = value['check_runs'] if isinstance(value, dict) else value
        rows.extend(items)
        if len(items) < 100:
            return rows
    raise ValueError('pagination bound exceeded; cannot claim complete snapshot')


def collect(repo, number):
    owner, name = repo.split('/')
    pr = gh('api', f'repos/{repo}/pulls/{number}')
    head = pr['head']['sha']
    threads, cursor = [], None
    for _ in range(100):
        args = ['api', 'graphql', '-f', f'query={QUERY}', '-f', f'owner={owner}',
                '-f', f'name={name}', '-F', f'number={number}']
        if cursor:
            args += ['-f', f'cursor={cursor}']
        value = gh(*args)
        if value.get('errors'):
            raise ValueError(f'GraphQL errors: {value["errors"]}')
        connection = value['data']['repository']['pullRequest']['reviewThreads']
        threads.extend(connection['nodes'])
        if not connection['pageInfo']['hasNextPage']:
            break
        cursor = connection['pageInfo']['endCursor']
    else:
        raise ValueError('thread pagination bound exceeded')
    data = dict(pr=pr, threads=threads,
        checks=pages(f'repos/{repo}/commits/{head}/check-runs'),
        statuses=pages(f'repos/{repo}/commits/{head}/statuses'),
        reviews=pages(f'repos/{repo}/pulls/{number}/reviews'),
        comments=pages(f'repos/{repo}/issues/{number}/comments'),
        inline_comments=pages(f'repos/{repo}/pulls/{number}/comments'))
    if gh('api', f'repos/{repo}/pulls/{number}')['head']['sha'] != head:
        raise ValueError('PR head changed while collecting; retry snapshot')
    return data


def is_coderabbit(item, contexts):
    """Centralized identity; names alone only match explicitly discovered statuses."""
    app = item.get('app') or {}
    creator = item.get('creator') or {}
    host = urlparse(item.get('details_url') or item.get('target_url') or '').hostname or ''
    return (app.get('slug') == 'coderabbitai' or creator.get('login') == BOT
            or host in ('coderabbit.ai', 'app.coderabbit.ai')
            or item.get('context') in contexts)


def gate(items):
    if not items:
        return 'missing'
    states = [i.get('conclusion') if 'conclusion' in i and i.get('status') == 'completed'
              else i.get('state', 'pending') for i in items]
    if any(s in ('failure', 'error', 'cancelled', 'timed_out', 'action_required', 'stale') for s in states):
        return 'failed'
    if any(s in (None, 'pending', 'queued', 'in_progress', 'waiting', 'requested') for s in states):
        return 'pending'
    if all(s == 'success' for s in states):
        return 'success'
    if any(s in ('skipped', 'neutral') for s in states):
        return 'skipped'
    return 'unknown'


def summarize(data, config, local_sha=None, addressed_sha=None):
    pr, head = data['pr'], data['pr']['head']['sha']
    # GitHub may retain reruns and multiple statuses: newest per producer/context wins.
    checks = {}
    for item in sorted(data['checks'], key=lambda i: i['id']):
        checks[((item.get('app') or {}).get('id'), item['name'])] = item
    statuses = {}
    for item in sorted(data['statuses'], key=lambda i: i['id']):
        statuses[item['context']] = item
    items = list(checks.values())+list(statuses.values())
    contexts = config.get('coderabbit_status_contexts', [])
    rabbit = [i for i in items if is_coderabbit(i, contexts)]
    ci = [i for i in items if not is_coderabbit(i, contexts)]
    ci_state = gate(ci)
    names = {i.get('name', i.get('context')) for i in ci}
    missing_required = sorted(set(config.get('required_checks', []))-names)
    if missing_required:
        ci_state = 'missing'
    rabbit_state = gate(rabbit)
    current_reviews = [r for r in data['reviews'] if r['user']['login'] == BOT
                       and r.get('commit_id') == head and r['state'] != 'PENDING']
    if rabbit_state == 'success':
        rabbit_state = 'complete' if current_reviews else 'unverified'
    # Only negative fallback hints: text never establishes successful completion.
    bot_comments = [c for c in data['comments'] if c['user']['login'] == BOT]
    latest = max(bot_comments, key=lambda c:c.get('updated_at', ''), default={}).get('body', '').lower()
    if rabbit_state in ('missing', 'pending', 'unverified'):
        if 'rate limit' in latest:
            rabbit_state = 'rate_limited'
        elif 'review skipped' in latest or 'review is skipped' in latest:
            rabbit_state = 'skipped'
    latest_human = {}
    for r in sorted(data['reviews'], key=lambda r:r['id']):
        if r['user']['login'] != BOT and r['state'] in ('APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'):
            latest_human[r['user']['login']] = r
    requested = [r for r in latest_human.values() if r['state'] == 'CHANGES_REQUESTED']
    bot_requested = bool(current_reviews and max(current_reviews,key=lambda r:r['id'])['state'] == 'CHANGES_REQUESTED')
    unresolved = [t for t in data['threads'] if not t['isResolved']]
    remote_green = (ci_state == 'success' and rabbit_state == 'complete' and
                    not unresolved and not requested and not bot_requested and not pr['draft'] and pr['state'] == 'open'
                    and pr.get('mergeable') is True)
    return dict(pr=pr['number'], head_sha=head, ci=ci_state, coderabbit=rabbit_state,
        check_names=sorted(names), coderabbit_surfaces=[i.get('name',i.get('context')) for i in rabbit],
        missing_required_checks=missing_required, unresolved_threads=len(unresolved),
        human_requested_changes=len(requested), comments=len(data['comments']),
        coderabbit_requested_changes=bot_requested,
        inline_comments=len(data['inline_comments']), current_coderabbit_reviews=len(current_reviews),
        remote_gates_green=remote_green,
        merge_ready=remote_green and local_sha == head and addressed_sha == head,
        attestation_required='Exact head local validation and all substantive summary/human/inline findings accounted for; helper cannot independently verify dispositions.',
        feedback=data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pr', type=int, required=True)
    parser.add_argument('--repo', default='Kesh3805/temporal-compute')
    parser.add_argument('--wait', action='store_true')
    parser.add_argument('--interval', type=int, default=45)
    parser.add_argument('--max-polls', type=int, default=10)
    parser.add_argument('--local-validated-sha')
    parser.add_argument('--findings-addressed-sha')
    args = parser.parse_args()
    if args.pr <= 0 or not re.fullmatch(r'[\w.-]+/[\w.-]+',args.repo):
        parser.error('positive PR and owner/repository required')
    if not 30 <= args.interval <= 60 or not 1 <= args.max_polls <= 40:
        parser.error('interval must be 30–60 seconds; max-polls must be 1–40')
    config = json.loads((ROOT/'.github/review-status.json').read_text(encoding='utf-8'))
    for poll in range(args.max_polls if args.wait else 1):
        result = summarize(collect(args.repo,args.pr),config,args.local_validated_sha,args.findings_addressed_sha)
        result['poll'] = poll+1
        print(json.dumps(result,ensure_ascii=True),flush=True)
        if result['merge_ready']:
            return 0
        if result['ci'] == 'failed' or result['coderabbit'] in ('failed','skipped','rate_limited'):
            return 1
        if result['remote_gates_green'] or not args.wait:
            return 1
        if result['ci'] not in ('pending','missing') and result['coderabbit'] not in ('pending','missing','unverified'):
            return 1
        if poll+1 < args.max_polls:
            time.sleep(args.interval)
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, subprocess.SubprocessError, OSError) as error:
        print(json.dumps({'merge_ready':False,'error':str(error)}),file=sys.stderr)
        sys.exit(3)
