import sys,re,json,difflib,statistics
from collections import Counter
sys.path.insert(0,'.'); from rec import *
TR=str.maketrans({'ي':'ی','ك':'ک','ى':'ی','ة':'ه','ۀ':'ه','أ':'ا','إ':'ا','آ':'ا','ٱ':'ا','ؤ':'و','ئ':'ی','ء':'','ـ':'','ً':'','ٌ':'','ٍ':'','َ':'','ُ':'','ِ':'','ّ':'','ْ':'','ٰ':'',**{chr(0x6F0+k):str(k) for k in range(10)},**{chr(0x660+k):str(k) for k in range(10)}})
def norm(s):
    s=s.translate(TR).replace('‌',' ')
    return re.sub(r'ا+لله','لله',s)
def words(s): return re.findall(r'[^\W\d_]+',norm(s))
def nums(s): return re.findall(r'\d+',norm(s))
vol=int(sys.argv[1])
t=open(f'/home/tabib/projects/apps/fahares-corpus/text/fankha/fankha_vol_{vol:02d}.txt').read()
parts=re.split(r'<!-- page: (\d+) -->',t); pg={}
for k in range(1,len(parts),2): pg[int(parts[k])]=pg.get(int(parts[k]),'')+parts[k+1]
cb={k:Counter(words(v)) for k,v in pg.items()}
idx=[i for i,l in enumerate(LABS) if l.split('-')[0]==str(vol)]
off=None; out=dict(vol=vol,pages=[],unmatched=[])
for i in idx:
    pl=' '.join(page_lines(i)); a=Counter(words(pl))
    if sum(a.values())<30: continue
    lab=int(LABS[i].split('-')[1])
    cands=range(lab-120,lab+10) if off is None else [lab+off+d for d in (0,-1,1,-2,2,-3,3)]
    best=None
    for c in cands:
        if c in cb:
            sc=sum((a&cb[c]).values())/max(1,sum(a.values()),sum(cb[c].values()))
            if not best or sc>best[0]: best=(sc,c)
    if not best or best[0]<0.6:
        out['unmatched'].append((i,LABS[i],best)); off=None; continue
    off=best[1]-lab; c=best[1]
    P=''.join(words(pl)); T=''.join(words(pg[c]))
    oT=cb[c]-a; oP=a-cb[c]
    tw=[w for w in oT if len(w)>=3 and not re.search(r'[A-Za-zā-ž]',w) and w not in P]
    pw=[w for w in oP if len(w)>=3 and not re.search(r'[A-Za-zā-ž]',w) and w not in T and w[::-1] not in T]
    pairs=[]
    for w in tw:
        m=difflib.get_close_matches(w,pw,1,0.6); pairs.append((w,m[0] if m else ''))
    pn=set(nums(pl)); pn|={x[::-1] for x in pn}; Pd=''.join(nums(pl))
    badn=[n for n in set(nums(pg[c])) if len(n)>=2 and n not in pn and n not in Pd and n[::-1] not in Pd]
    out['pages'].append(dict(pdf=i,page=c,score=round(best[0],3),pairs=pairs,extraP=[w for w in pw if not any(w==p[1] for p in pairs)],badnum=badn))
out['corpus_pages']=len(pg)
json.dump(out,open(f'full_{vol:02d}.json','w'),ensure_ascii=False)
sc=[p['score'] for p in out['pages']]
print(vol,'matched',len(sc),'/',len(pg),'unmatched',len(out['unmatched']),'median',statistics.median(sc) if sc else '-','pairs',sum(len([q for q in p['pairs'] if q[1]]) for p in out['pages']),'unpaired',sum(len([q for q in p['pairs'] if not q[1]]) for p in out['pages']),'badnum',sum(len(p['badnum']) for p in out['pages']),flush=True)
