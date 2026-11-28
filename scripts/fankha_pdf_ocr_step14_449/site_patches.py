"""Word patches for the site's Fankha text fields from the step 14.449 fixes (fahares step 14.449).
Each fix (vol, page, old word, new word, the old text around it) is looked for in the text fields of the works, copies
and notes whose Fankha entry spans that page. An occurrence counts when the word stands whole and its context on one
side matches the corpus; a field with exactly one such occurrence gets a patch: the shortest stretch around the word
that occurs once in the field, and the same stretch with the new word."""
import csv,json,re,sys,collections,difflib
sys.path.insert(0,'judge')
items={x['id']:x for x in json.load(open('judge/items.json'))}
F={r['id']:r for r in csv.DictReader(open('judge/final.tsv'),delimiter='\t')}
src=open('judge/apply.py').read()
ns={'re':re}; exec(src[src.index('def form'):src.index('byvol=')],ns); form=ns['form']; drops=ns['pdf_drops_alef']
OLD='/home/tabib/projects/apps/fahares-corpus/text/fankha'
import subprocess
texts={v:subprocess.run(['git','-C','/home/tabib/projects/apps/fahares-corpus','show',f'e71cd0b^:text/fankha/fankha_vol_{v:02d}.txt'],capture_output=True,text=True,check=True).stdout for v in range(1,35)}
fixes=[]
for i,r in F.items():
    if r['verdict']!='PRINT': continue
    x=items[i]; t=texts[x['vol']]; a,b=x['tpos']
    if t[a:b]!=x['traw']: continue
    new=form(x['traw'],x['praw'])
    if new==x['traw'] or drops(x['traw'],new): continue
    ls=t.rfind('\n',0,a)+1
    if t[ls:ls+1]=='●': continue
    fixes.append(dict(id=i,vol=x['vol'],page=x['page'],old=x['traw'],new=new,L=t[max(ls,a-30):a],R=t[b:t.find('\n',b) if t.find('\n',b)>0 else b+30][:30]))
print('fixes',len(fixes))
LET=r'[^\W\d_]|[ً-ْٰـء‌]'
def nrm(s): return re.sub(r'[\s‌]+','',s)
TEXTCOLS={'work':['entry_text','description','incipit_text','explicit_text','print_info','dedication','composition_place','composition_date_raw','raw_text'],
 'copy':['copy_text','incipit_text','explicit_text','binding','paper','copy_place','copy_date_raw','copy_date_note','commissioned_by','raw_text'],
 'note':['text']}
NAMECOLS={'work':['author_name'],'copy':['scribe_name']}
bypage=collections.defaultdict(list)
for f in fixes: bypage[(f['vol'],f['page'])].append(f)
patches=collections.defaultdict(list); stat=collections.Counter(); names=[]
hit_fix=set()
for line in open('site/site.jsonl'):
    r=json.loads(line)
    if r['vol'] is None or r['p1'] is None: continue
    for pg in range(r['p1'],(r['p2'] or r['p1'])+1):
        for f in bypage.get((r['vol'],pg),()):
            rx=re.compile(r'(?<!'+LET+')'+re.escape(f['old'])+r'(?!'+LET+')')
            for col in TEXTCOLS[r['t']]+NAMECOLS.get(r['t'],[]):
                v=r.get(col)
                if not v: continue
                occ=[m for m in rx.finditer(v) if nrm(v[max(0,m.start()-20):m.start()])[-5:]==nrm(f['L'])[-5:] or nrm(v[m.end():m.end()+20])[:5]==nrm(f['R'])[:5]]
                if not occ: continue
                if len(occ)>1: stat['ambiguous']+=1; continue
                if col in NAMECOLS.get(r['t'],[]): names.append((r['t'],r['id'],col,v,f['old'],f['new'])); stat['name_col']+=1; continue
                m=occ[0]; k=0
                while True:
                    seg=v[max(0,m.start()-k):m.end()+k]
                    if v.count(seg)==1 or k>60: break
                    k+=2
                if v.count(seg)!=1: stat['not_unique']+=1; continue
                newseg=v[max(0,m.start()-k):m.start()]+f['new']+v[m.end():m.end()+k]
                key=(r['t'],r['id'] if r['t']!='work' or col!='entry_text' else r['id'],col)
                if col in ('entry_text','copy_text'):
                    key=('entry',r['entry_id'],'entry_text' if r['t']=='work' else 'copy_text')
                    if r['text_status']=='edited': stat['entry_edited']+=1; continue
                if any(p['old']==seg for p in patches[key]): continue
                patches[key].append(dict(old=seg,new=newseg,fix=f['id'])); stat['patch']+=1; hit_fix.add(f['id'])
print(dict(stat)); print('fixes reaching the site',len(hit_fix),'of',len(fixes))
c=collections.Counter((k[0],k[2]) for k in patches)
for k,n in c.most_common(): print(n,k)
out=[dict(table=k[0],id=k[1],column=k[2],patches=v) for k,v in patches.items()]
json.dump(dict(step='14.449',patches=out),open('site/patches.json','w'),ensure_ascii=False)
json.dump(names,open('site/name_cols.json','w'),ensure_ascii=False)
