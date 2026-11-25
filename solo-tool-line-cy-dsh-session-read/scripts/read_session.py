#!/usr/bin/env python3
"""Read and search DSH session archives (zstd JSONL event streams)."""
import argparse, collections, io, json, os
from datetime import datetime, timezone
import zstandard

ROOT = r"C:\Users\admin\.dsh\sessions"


def decode_ws(name):
    """Reverse the workspace-dir encoding: ~XXXX hex codepoints -> chars."""
    s = name.strip('-')
    out, i = [], 0
    while i < len(s):
        if s[i] == '~' and i + 5 <= len(s):
            try:
                out.append(chr(int(s[i + 1:i + 5], 16)))
                i += 5
                continue
            except ValueError:
                pass
        out.append(s[i])
        i += 1
    return ''.join(out)


def find_sessions(ws_kw, sess_kw):
    hits = []
    for d in os.listdir(ROOT):
        full = os.path.join(ROOT, d)
        if not os.path.isdir(full):
            continue
        dec = decode_ws(d)
        if ws_kw and ws_kw.lower() not in dec.lower() and ws_kw.lower() not in d.lower():
            continue
        for sd in os.listdir(full):
            if not sd.startswith('session-'):
                continue
            if sess_kw and sess_kw.lower() not in sd.lower():
                continue
            z = os.path.join(full, sd, 'session.v4.jsonl.zstd')
            if os.path.isfile(z):
                hits.append((dec, sd, z))
    return hits


def extract_text(o):
    """Best-effort: pull the most informative string out of the event's data."""
    d = o.get('data')
    if d is None:
        return ''
    if isinstance(d, str):
        return d
    if isinstance(d, dict):
        for k in ('text', 'content', 'message', 'title', 'body'):
            v = d.get(k)
            if isinstance(v, str):
                return v
        best = ''

        def walk(x):
            nonlocal best
            if isinstance(x, str):
                if len(x) > len(best):
                    best = x
            elif isinstance(x, dict):
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)

        walk(d)
        return best
    return str(d)


def to_ms(v):
    """int/numeric-string -> epoch ms; None otherwise."""
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def arg_to_ms(v):
    """Accept epoch ms or ISO datetime; return epoch ms or None."""
    if not v:
        return None
    v = str(v).strip()
    if v.isdigit():
        return int(v)
    try:
        dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description='Read/search DSH session archives')
    ap.add_argument('--list-sessions', action='store_true', help='list all workspaces and session ids')
    ap.add_argument('--workspace', help='fuzzy keyword for the workspace (Chinese OK)')
    ap.add_argument('--session', help='session-id fragment filter')
    ap.add_argument('--role', choices=['user', 'assistant', 'tool', 'all'], default='all')
    ap.add_argument('--grep', help='keyword inside message text or event type')
    ap.add_argument('--since', help='epoch ms or ISO datetime lower bound')
    ap.add_argument('--until', help='epoch ms or ISO datetime upper bound')
    ap.add_argument('--last', type=int, default=20, help='keep last N matches')
    ap.add_argument('--max-len', type=int, default=280, help='truncate extracted text to N chars')
    ap.add_argument('--show-json', action='store_true', help='print raw JSON rows instead of extracted text')
    ap.add_argument('--stats', action='store_true', help='print event-type counts instead of rows')
    a = ap.parse_args()
    since_ms = arg_to_ms(a.since)
    until_ms = arg_to_ms(a.until)

    if a.list_sessions:
        for d in sorted(os.listdir(ROOT)):
            p = os.path.join(ROOT, d)
            if not os.path.isdir(p):
                continue
            for sd in sorted(os.listdir(p)):
                if not sd.startswith('session-'):
                    continue
                z = os.path.join(p, sd, 'session.v4.jsonl.zstd')
                if os.path.isfile(z):
                    print(f"{decode_ws(d)}  |  {sd}  [{os.path.getsize(z)}B]")
        return

    hits = find_sessions(a.workspace, a.session)
    if not hits:
        print('NO MATCHING SESSION - try --list-sessions')
        return
    print(f"# {len(hits)} session(s) matched")

    role_map = {'user': 'user/message', 'assistant': 'assistant/message',
                'tool': 'tool/call'}

    for dec, sd, z in hits:
        print(f"== {dec} | {sd} ==")
        dctx = zstandard.ZstdDecompressor()
        matched = []
        types = collections.Counter()
        with open(z, 'rb') as fi:
            with dctx.stream_reader(fi) as r:
                t = io.TextIOWrapper(r, encoding='utf-8', errors='replace')
                for line in t:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    ty = o.get('type', '')
                    types[ty] += 1
                    if a.role != 'all' and ty != role_map.get(a.role, ty):
                        continue
                    txt = extract_text(o)
                    if a.grep:
                        g = a.grep.lower()
                        if g not in (txt or '').lower() and g not in ty.lower():
                            continue
                    tm = to_ms(o.get('time'))
                    if tm is not None:
                        if since_ms is not None and tm < since_ms:
                            continue
                        if until_ms is not None and tm > until_ms:
                            continue
                    matched.append(o)
        if a.stats:
            print('  TYPES:', dict(types))
            continue
        for o in matched[-a.last:]:
            ts, ty = o.get('time', ''), o.get('type', '')
            if a.show_json:
                body = json.dumps(o, ensure_ascii=False)[:a.max_len * 4]
            else:
                body = extract_text(o).replace('\n', ' / ')
                if len(body) > a.max_len:
                    body = body[:a.max_len] + '…'
            print(f"[{ts}] {ty}: {body}")
        if not matched:
            print('  (no matching rows)')


if __name__ == '__main__':
    main()