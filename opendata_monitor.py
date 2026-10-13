#!/usr/bin/env python3
"""opendata.swiss metadata monitor for organization kanton-bern-2; Python stdlib only."""
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent
ORG = 'kanton-bern-2'
BASE = 'https://ckan.opendata.swiss/api/3/action/package_search'
STORE = ROOT / 'data' / 'opendata' / 'snapshots'
PUBLIC = ROOT / 'docs' / 'opendata'
HEADERS = {'Accept':'application/json','User-Agent':'Bern-Public-Metadata-Monitor/1.0'}

def load_page(start, rows=100):
    params = urllib.parse.urlencode({'fq':'organization:'+ORG,'rows':rows,'start':start,'sort':'id asc'})
    url = BASE + '?' + params
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=50) as res:
                data=json.load(res)
            if data.get('success') is not True or not isinstance(data.get('result'),dict):
                raise RuntimeError('Ungültige CKAN-Antwort')
            return data['result']
        except Exception:
            if attempt==3: raise
            time.sleep(2**attempt)

def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    temp.replace(path)

def fetch():
    collected={}
    count=None
    offset=0
    for page in range(100):
        reply=load_page(offset)
        batch=reply.get('results')
        if not isinstance(batch,list) or not isinstance(reply.get('count'),int):
            raise RuntimeError('Ungültige Pagination')
        if count is None: count=reply['count']
        if reply['count']!=count: raise RuntimeError('Anzahl während Abruf verändert; kein Tagesstand gespeichert')
        for record in batch:
            uid=record.get('id')
            org=record.get('organization') or {}
            if not uid or uid in collected or org.get('name')!=ORG:
                raise RuntimeError('Ungültige ID oder abweichende Organisation; Abbruch')
            collected[uid]=record
        offset+=len(batch)
        if offset>=count: break
        if not batch: raise RuntimeError('Unvollständiger Abruf')
    else: raise RuntimeError('Seitenlimit überschritten')
    if not collected or len(collected)!=count:
        raise RuntimeError(f'Unvollständige/leer Antwort: {len(collected)} / {count}')
    return dict(sorted(collected.items()))

def diff(a,b):
    changed=[]
    for key in sorted(set(a)|set(b)):
        if key not in a: kind='new'
        elif key not in b: kind='removed'
        elif a[key]!=b[key]: kind='changed'
        else: continue
        record=b.get(key) or a[key]
        name=record.get('title') or record.get('name') or key
        if isinstance(name,dict): name=name.get('de') or next(iter(name.values()),key)
        changed.append({'id':key,'title':str(name),'kind':kind})
    return changed

def main():
    today=dt.datetime.now(ZoneInfo('Europe/Zurich')).date().isoformat()
    STORE.mkdir(parents=True,exist_ok=True)
    old_files=sorted(p for p in STORE.glob('????-??-??.json') if p.stem<today)
    prev=old_files[-1] if old_files else None
    old=json.loads(prev.read_text(encoding='utf-8'))['datasets'] if prev else {}
    current=fetch()
    changes=diff(old,current) if prev else []
    summary={k:sum(c['kind']==k for c in changes) for k in ('new','removed','changed')}
    write(STORE/(today+'.json'),{'date':today,'organization':ORG,'datasets':current})
    write(ROOT/'data'/'opendata'/'reports'/(today+'.json'),{'date':today,'comparedWith':prev.stem if prev else None,'initial':prev is None,'count':len(current),'summary':summary,'changes':changes})
    reports=[]
    for f in sorted((ROOT/'data'/'opendata'/'reports').glob('????-??-??.json'),reverse=True):
        r=json.loads(f.read_text(encoding='utf-8'))
        reports.append({'date':r['date'],'count':r['count'],'summary':r['summary']})
    for src in sorted(STORE.glob('????-??-??.json')):
        dest=PUBLIC/'snapshots'/src.name
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists() or src.read_bytes()!=dest.read_bytes(): dest.write_bytes(src.read_bytes())
    write(PUBLIC/'index.json',{'organization':ORG,'latest':today,'reports':reports})
    print(f'opendata.swiss: {len(current)} Datensätze gespeichert; Änderungen: {summary}')

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('opendata.swiss Abruf FEHLER:',exc,file=sys.stderr)
        sys.exit(1)
