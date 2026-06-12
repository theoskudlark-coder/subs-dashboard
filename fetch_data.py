#!/usr/bin/env python3
"""
Fetches all dashboard data from Monday.com and writes data.json.
Run by GitHub Actions every 30 minutes.
"""
import json, os, sys
from datetime import datetime, timezone
import urllib.request, urllib.error

TOKEN = os.environ.get('MONDAY_TOKEN', '')
if not TOKEN:
    print('ERROR: MONDAY_TOKEN env var not set', file=sys.stderr)
    sys.exit(1)

API_URL = 'https://api.monday.com/v2'
BOARD_SR = 4969640884
BOARD_SS = 9812976093

SR_GROUPS = ['new_group43773', 'new_group87137', 'new_group45268', 'new_group613', 'topics', 'group_title']
SS_GROUPS = ['group_title', 'group_mktsz4af', 'group_mkv54q2j']

SR_COLS = ['person', 'status81', 'numbers', 'numbers0', 'date4']
SS_COLS = ['status', 'numeric_mkts722d', 'numeric_mktsck8h', 'date4']


def gql(query):
    payload = json.dumps({'query': query}).encode('utf-8')
    req = urllib.request.Request(API_URL, data=payload, headers={
        'Authorization': TOKEN,
        'Content-Type': 'application/json',
        'API-Version': '2024-10',
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    if 'errors' in data:
        raise RuntimeError(f'GraphQL error: {data["errors"]}')
    return data['data']


def fetch_group(board_id, group_id, col_ids):
    cols = ','.join(f'"{c}"' for c in col_ids)
    items, cursor, first = [], None, True
    while first or cursor:
        first = False
        if cursor:
            page_args = f'limit:500,cursor:"{cursor}"'
        else:
            page_args = (
                f'limit:500,query_params:{{rules:[{{'
                f'column_id:"group",compare_value:["{group_id}"],operator:any_of'
                f'}}]}}'
            )
        q = (f'{{boards(ids:[{board_id}]){{items_page({page_args})'
             f'{{cursor items{{name column_values(ids:[{cols}]){{id value text}}}}}}}}}')
        data = gql(q)
        pg = data['boards'][0]['items_page']
        items.extend(pg['items'])
        cursor = pg.get('cursor') or None
        print(f'  {group_id}: {len(items)} items so far...')
    return items


result = {
    'fetched_at': datetime.now(timezone.utc).isoformat(),
    'board_sr': {},
    'board_ss': {},
}

for gid in SR_GROUPS:
    print(f'Fetching SR {gid}')
    try:
        result['board_sr'][gid] = fetch_group(BOARD_SR, gid, SR_COLS)
    except Exception as e:
        print(f'  WARNING: {e}', file=sys.stderr)
        result['board_sr'][gid] = []

for gid in SS_GROUPS:
    print(f'Fetching SS {gid}')
    try:
        result['board_ss'][gid] = fetch_group(BOARD_SS, gid, SS_COLS)
    except Exception as e:
        print(f'  WARNING: {e}', file=sys.stderr)
        result['board_ss'][gid] = []

with open('data.json', 'w') as f:
    json.dump(result, f)

total = sum(len(v) for v in result[)board_sr'].values()) + sum(len(v) for v in result['board_ss'].values())
print(f'Done — {total} total items written to data.json')
