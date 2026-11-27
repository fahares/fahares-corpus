import sys,re,json,unicodedata
from collections import Counter
sys.path.insert(0,'.'); from rec import *
RM='ءـًٌٍَُِّْٰ'
TR=str.maketrans({'ي':'ی','ك':'ک','ى':'ی','ة':'ه','ۀ':'ه','أ':'ا','إ':'ا','آ':'ا','ٱ':'ا','ؤ':'و','ئ':'ی',**{c:'' for c in RM}})
WRE=re.compile(r'(?:[^\W\d_]|[ً-ْٰـء])+')
def n(w): return re.sub(r'ا+لله','لله',w.translate(TR))
def toks(s):  # list of (norm, raw, start, end)
    out=[]
    for m in WRE.finditer(s):
        r=m.group(); x=n(r)
        if x and not re.search(r'[A-Za-zā-žḥṣḍṭẓ]',r): out.append((x,r,m.start(),m.end()))
    return out
def lev(a,b):
    if abs(len(a)-len(b))>2: return 9
    p=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        c=[i]
        for j,cb in enumerate(b,1): c.append(min(p[j]+1,c[j-1]+1,p[j-1]+(ca!=cb)))
        p=c
    return p[-1]
vol=int(sys.argv[1])
t=open(f'/home/tabib/projects/apps/fahares-corpus/text/fankha/fankha_vol_{vol:02d}.txt').read()
# page spans in file
marks=[(m.start(),m.end(),int(m.group(1))) for m in re.finditer(r'<!-- page: (\d+) -->',t)]
spans={}
for k,(s,e,pgno) in enumerate(marks):
    end=marks[k+1][0] if k+1<len(marks) else len(t)
    spans.setdefault(pgno,[]).append((e,end))
full=json.load(open(f'full_{vol:02d}.json'))
pdfcnt=Counter(); txtcnt=Counter(); cands=[]
pdf_lines={}
for pg in full['pages']:
    i,c=pg['pdf'],pg['page']
    L=page_lines(i); pdf_lines[c]=L
    P=toks(' \n '.join(L)); Pn=[x[0] for x in P]
    T=[]
    for (s,e) in spans[c]:
        T+=[(x,r,a+s,b+s) for (x,r,a,b) in toks(t[s:e])]
    Tn=[x[0] for x in T]
    pc=Counter(Pn); tc=Counter(Tn)
    pdfcnt.update(Pn); txtcnt.update(Tn)
    onlyT=[w for w in tc if w not in pc and len(w)>=3]
    onlyP=[w for w in pc if w not in tc and len(w)>=3]
    for w in onlyT:
        if tc[w]!=1: continue
        k=Tn.index(w)
        nb={Tn[j] for j in (k-2,k-1,k+1,k+2) if 0<=j<len(Tn) and len(Tn[j])>=2}
        tnear={Tn[x] for x in range(k-2,k+3) if 0<=x<len(Tn) and x!=k}
        best=[]
        for q in onlyP:
            d=lev(w,q)
            if d>2 or d>=len(w)-1: continue
            js=[j for j,x in enumerate(Pn) if x==q]
            if len(js)!=1: continue
            j=js[0]
            near={Pn[x] for x in range(j-2,j+3) if 0<=x<len(Pn) and x!=j}
            split=False
            for aa,bb,nn in ((w,q,near),(q,w,tnear)):
                if aa.startswith(bb) and aa[len(bb):] in nn: split=True
                if aa.endswith(bb) and aa[:len(aa)-len(bb)] in nn: split=True
            if split: continue
            pnb={Pn[x] for x in range(j-3,j+4) if 0<=x<len(Pn) and x!=j}
            sup=len(nb&pnb)
            if sup: best.append((d,-sup,q,P[j][1]))
        best.sort()
        if best and (len(best)==1 or best[0][:2]<best[1][:2]):
            d,ns,q,praw=best[0]
            cands.append(dict(vol=vol,page=c,pdf=i,t=w,traw=T[k][1],tpos=[T[k][2],T[k][3]],p=q,praw=unicodedata.normalize('NFKC',praw),dist=d,sup=-ns,
                              ctx=t[max(0,T[k][2]-40):T[k][3]+40]))
json.dump(dict(cands=cands,pdfcnt=pdfcnt,txtcnt=txtcnt),open(f'pairs_{vol:02d}.json','w'),ensure_ascii=False)
print(vol,len(cands),flush=True)
