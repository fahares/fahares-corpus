import csv,json,subprocess,collections,re
R=list(csv.DictReader(open('/home/tabib/projects/apps/fahares-corpus/.claude/worktrees/fankha-pdf-ocr/reconciliations/fankha_ocr_names_step14_451.tsv'),delimiter='\t'))
def q(sql):
    out=subprocess.run(['docker','exec','fahares_mariadb','sh','-c',f'mariadb -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" -N -B fahares_prod -e \'{sql}\''],capture_output=True,text=True).stdout
    return [l.split('\t') for l in out.rstrip('\n').split('\n') if l]
cop=sorted({r['site_id'] for r in R if r['record']=='copy'}); wor=sorted({r['site_id'] for r in R if r['record']=='work'})
links=collections.defaultdict(list)
for mid,pid,name in q(f"select manuscript_id,person_id,name from manuscript_people where role=\"scribe\" and manuscript_id in ({','.join(cop)})"): links[('copy',mid)].append((pid,name))
for wid,pid,name in q(f"select work_id,person_id,name from work_people where role=\"author\" and work_id in ({','.join(wor)})"): links[('work',wid)].append((pid,name))
title={}
for i,t in q(f"select m.id,w.primary_title from manuscripts m join works w on w.id=m.work_id where m.id in ({','.join(cop)})"): title[('copy',i)]=t
for i,t in q(f"select id,primary_title from works where id in ({','.join(wor)})"): title[('work',i)]=t
pids={p for v in links.values() for p,_ in v if p!='NULL'}
P={r[0]:r for r in q(f"select id,name,ifnull(life_dates_raw,\"\"),ifnull(death_year_hijri,\"\"),works_count,manuscripts_count,ifnull(aliases,\"\"),ifnull(wrong_names,\"\") from people where id in ({','.join(pids)})")}
# where the record sits in Fankha, for the corpus line
loc={}
for line in open('site/site.jsonl'):
    if '"t": "note"' in line[:20]: continue
    r=json.loads(line); loc[(r['t'],str(r['id']))]=(r['vol'],r['p1'],r['p2'])
texts={}
def corpus_line(vol,p1,p2,old):
    if vol not in texts:
        texts[vol]=subprocess.run(['git','-C','/home/tabib/projects/apps/fahares-corpus','show',f'e71cd0b^:text/fankha/fankha_vol_{vol:02d}.txt'],capture_output=True,text=True).stdout
    t=texts[vol]; a=t.find(f'<!-- page: {p1} -->'); b=t.find(f'<!-- page: {(p2 or p1)+1} -->',a+1)
    seg=t[a: b if b>0 else a+20000]
    for l in seg.split('\n'):
        if old in l and len(l)<400: return l.strip()
    return ''
out=[]
for n,r in enumerate(R):
    k=(r['record'],r['site_id']); L=links.get(k,[])
    pers=[P[p] for p,_ in L if p in P]
    hit=[p for p in pers if r['old'] in p[1]] or pers
    p=hit[0] if hit else None
    cand=''
    if p:
        newname=p[1].replace(r['old'],r['new'])
        m=q(f"select id,name,ifnull(life_dates_raw,\"\"),works_count+manuscripts_count from people where name={json.dumps(newname)} limit 3")
        cand='; '.join(f'#{x[0]} {x[1]} ({x[2]}) {x[3]} records' for x in m)
    vol,p1,p2=loc.get(k,(None,None,None))
    out.append(dict(n=n,record=r['record'],site_id=r['site_id'],column=r['column'],site_value=r['site_value'],old=r['old'],new=r['new'],
        title=title.get(k,''),person_id=p[0] if p else '',person_name=p[1] if p else '',person_dates=(p[2] or p[3]) if p else '',
        person_records=(int(p[4])+int(p[5])) if p else '',aliases=p[6] if p else '',wrong_names=p[7] if p else '',
        person_with_corrected_name=cand,corpus_line=corpus_line(vol,p1,p2,r['old']) if vol else ''))
cols=list(out[0].keys())
with open('site/names_batch.tsv','w') as f:
    w=csv.DictWriter(f,cols,delimiter='\t',lineterminator='\n'); w.writeheader(); w.writerows(out)
print(len(out), sum(1 for o in out if o['person_with_corrected_name']), sum(1 for o in out if not o['corpus_line']))
