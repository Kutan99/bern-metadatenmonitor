#!/usr/bin/env python3
"""I14Y Bern public dataset metadata monitor; stdlib only (runs in GitHub Actions)."""
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / 'data'
DOCS = ROOT / 'docs'
BASE = 'https://api.i14y.admin.ch/api/public/v1'
PUBLISHER = 'CH_KT_BERN'
PAGE_SIZE = 100
MAX_PAGES = 500
HEADERS = {'Accept': 'application/json', 'User-Agent': 'I14Y-Bern-Metadata-Monitor/1.0 (GitHub Actions)'}


def get(path, params=None):
    url = BASE + path + ('?' + urllib.parse.urlencode(params) if params else '')
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=45) as res:
                return json.load(res)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            if attempt == 3:
                raise RuntimeError(f'API-Abruf fehlgeschlagen: {url}: {exc}') from exc
            time.sleep(2 ** attempt)


def extract_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ('data', 'items', 'results', 'datasets'):
            if isinstance(payload.get(key), list):
                return payload[key]
            if isinstance(payload.get(key), dict):
                nested = payload[key]
                for k in ('items', 'data', 'results'):
                    if isinstance(nested.get(k), list):
                        return nested[k]
    raise RuntimeError('Unbekanntes API-Listenformat. Kein Stand gespeichert.')


def total_count(payload):
    if not isinstance(payload, dict):
        return None
    for parent in (payload, payload.get('pagination'), payload.get('meta')):
        if isinstance(parent, dict):
            for key in ('totalItems', 'totalCount', 'total', 'totalElements'):
                if isinstance(parent.get(key), int):
                    return parent[key]
    return None


def identity(record):
    return str(record.get('id') or record.get('identifier') or '')


def canon(record):
    # JSON normalization avoids changes from property ordering only.
    return json.loads(json.dumps(record, ensure_ascii=False, sort_keys=True))


def fetch_all():
    rows = []
    seen = set()
    expected = None
    for page in range(1, MAX_PAGES + 1):
        payload = get('/datasets', {'publisherIdentifier': PUBLISHER, 'publicationLevel': 'Public', 'page': page, 'pageSize': PAGE_SIZE})
        batch = extract_list(payload)
        if expected is None:
            expected = total_count(payload)
        for item in batch:
            key = identity(item)
            if not key or key in seen:
                raise RuntimeError('Ungültige oder doppelte ID während Pagination. Kein Stand gespeichert.')
            seen.add(key)
            rows.append(item)
        if not batch or len(batch) < PAGE_SIZE or (expected is not None and len(rows) >= expected):
            break
    else:
        raise RuntimeError('Maximale Seitenzahl erreicht. Kein Stand gespeichert.')
    if expected is not None and len(rows) != expected:
        raise RuntimeError(f'Unvollständiger Abruf: {len(rows)} von {expected}. Kein Stand gespeichert.')
    # Get full metadata, not only listing summaries.
    full = {}
    for index, item in enumerate(rows, 1):
        key = identity(item)
        obj = get('/datasets/' + urllib.parse.quote(str(item['id']), safe='')) if item.get('id') else item
        if isinstance(obj, dict) and isinstance(obj.get('data'), dict):
            obj = obj['data']
        if not isinstance(obj, dict):
            raise RuntimeError(f'Unerwartete Detailantwort für {key}.')
        if str(obj.get('id') or key) != key:
            raise RuntimeError(f'ID-Abweichung für {key}.')
        level = str(obj.get('publicationLevel') or item.get('publicationLevel') or '')
        if level and level.lower() != 'public':
            raise RuntimeError(f'Nichtöffentlicher Datensatz in Antwort: {key}')
        full[key] = canon(obj)
        if index % 25 == 0:
            print(f'Details: {index}/{len(rows)}', flush=True)
        time.sleep(0.08)
    if not full:
        raise RuntimeError('Keine Datensätze zurückgegeben. Zum Schutz bestehender Stände abgebrochen.')
    return dict(sorted(full.items()))


def walk_diff(old, new, path=''):
    if isinstance(old, dict) and isinstance(new, dict):
        result = []
        for key in sorted(set(old) | set(new)):
            field = f'{path}.{key}' if path else key
            if key not in old:
                result.append({'field': field, 'before': None, 'after': new[key]})
            elif key not in new:
                result.append({'field': field, 'before': old[key], 'after': None})
            else:
                result.extend(walk_diff(old[key], new[key], field))
        return result
    # Arrays are compared as complete fields to avoid misleading index diffs.
    if old != new:
        return [{'field': path, 'before': old, 'after': new}]
    return []


def name(record):
    for key in ('title', 'name', 'identifier'):
        x = record.get(key)
        if isinstance(x, str) and x:
            return x
        if isinstance(x, dict):
            return x.get('de') or x.get('fr') or next((v for v in x.values() if isinstance(v, str)), '')
    return record.get('id', '(ohne Titel)')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temp.replace(path)


def main():
    today = dt.datetime.now(dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=0))).date().isoformat()
    # Workflow runs at 06:15 Zurich time; its UTC calendar day equals Zurich calendar day.
    if os.getenv('MONITOR_DATE'):
        today = os.environ['MONITOR_DATE']
    snapshots = DATA / 'snapshots'
    snapshots.mkdir(parents=True, exist_ok=True)
    prior = sorted(p for p in snapshots.glob('????-??-??.json') if p.stem < today)
    previous_file = prior[-1] if prior else None
    previous = json.loads(previous_file.read_text(encoding='utf-8'))['datasets'] if previous_file else {}
    current = fetch_all()
    changes = []
    for key in sorted(set(previous) | set(current)):
        before = previous.get(key)
        after = current.get(key)
        if before is None:
            changes.append({'id': key, 'title': name(after), 'kind': 'new', 'fields': []})
        elif after is None:
            changes.append({'id': key, 'title': name(before), 'kind': 'removed', 'fields': []})
        else:
            fields = walk_diff(before, after)
            if fields:
                changes.append({'id': key, 'title': name(after), 'kind': 'changed', 'fields': fields})
    summary = {kind: sum(c['kind'] == kind for c in changes) for kind in ('new', 'removed', 'changed')}
    report = {'date': today, 'comparedWith': previous_file.stem if previous_file else None, 'publisher': PUBLISHER,
              'count': len(current), 'previousCount': len(previous), 'initial': previous_file is None,
              'summary': summary, 'changes': [] if previous_file is None else changes}
    write_json(snapshots / (today + '.json'), {'date': today, 'publisher': PUBLISHER, 'datasets': current})
    write_json(DATA / 'reports' / (today + '.json'), report)
    reports = []
    for f in sorted((DATA / 'reports').glob('????-??-??.json'), reverse=True):
        r = json.loads(f.read_text(encoding='utf-8'))
        reports.append({'date': r['date'], 'comparedWith': r.get('comparedWith'), 'initial': r['initial'], 'count': r['count'], 'summary': r['summary'], 'file': f.name})
    # Make every archived snapshot available for arbitrary browser-side date comparisons.
    # Previously saved snapshots are also published during the next successful run.
    for source in sorted(snapshots.glob('????-??-??.json')):
        target = DOCS / 'snapshots' / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != source.read_bytes():
            target.write_bytes(source.read_bytes())
    write_json(DOCS / 'index.json', {'publisher': PUBLISHER, 'latest': today, 'reports': reports})
    write_json(DOCS / 'reports' / (today + '.json'), report)
    print(f'Erfolg: {len(current)} Datensätze; {summary}; Basis: {report["comparedWith"]}', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'FEHLER: {exc}', file=sys.stderr)
        sys.exit(1)
