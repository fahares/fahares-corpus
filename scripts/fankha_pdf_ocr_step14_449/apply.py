"""Apply PRINT verdicts to the Fankha text files: the OCR word is replaced by the printed word.
Usage: apply.py [--write]   (default: dry run, prints counts and a sample)"""
import sys,json,csv,glob,re,collections
CORPUS=sys.argv[sys.argv.index('--corpus')+1] if '--corpus' in sys.argv else '/home/tabib/projects/apps/fahares-corpus/text/fankha'
items={x['id']:x for x in json.load(open('judge/items.json'))}
V={r['id']:r for r in csv.DictReader(open('judge/final.tsv'),delimiter='\t')}
def form(traw,praw):
    arabic=bool(re.search('[يك]',traw))
    s=praw if arabic else praw.replace('ي','ی').replace('ك','ک')
    if not arabic and not re.search('[ىي]',traw): s=s.replace('ى','ی')
    if traw.endswith('ى') and s.endswith('ی'): s=s[:-1]+'ى'
    return s
import difflib
def pdf_drops_alef(old,new):
    # the PDF layer loses one alef of «اا» («هذاالکتاب» comes out «هذالکتاب»): keep the text there
    for o,i,j,k,l in difflib.SequenceMatcher(None,old,new).get_opcodes():
        if o=='delete' and old[i:j]=='ا' and ('اا' in old[max(0,i-1):j+1]): return True
    return False
byvol=collections.defaultdict(list)
for i,r in V.items():
    if r['verdict']=='PRINT': byvol[items[i]['vol']].append(items[i])
stat=collections.Counter(); sample=[]
log=[]; heading=[]
for vol,L in sorted(byvol.items()):
    path=f'{CORPUS}/fankha_vol_{vol:02d}.txt'; t=open(path).read()
    for x in sorted(L,key=lambda x:-x['tpos'][0]):
        a,b=x['tpos']
        if t[a:b]!=x['traw']: stat['stale']+=1; continue
        new=form(x['traw'],x['praw'])
        if pdf_drops_alef(x['traw'],new): stat['alef_kept']+=1; continue
        ls=t.rfind('\n',0,a)+1
        if t[ls:ls+1]=='●':   # heading lines: title and standardised subject feed the site's work matching; reviewed apart
            stat['heading_kept']+=1; heading.append(dict(vol=vol,page=x['page'],old=x['traw'],new=new,line=t[ls:t.find('\n',a)])); continue
        if new==x['traw']: stat['same']+=1; continue
        t=t[:a]+new+t[b:]; stat['applied']+=1
        log.append(dict(vol=vol,page=x['page'],old=x['traw'],new=new))
    if '--write' in sys.argv: open(path,'w').write(t)
print(dict(stat), 'volumes',len(byvol))
import random; random.seed(1)
for l in random.sample(log,15): print(l)
json.dump(log,open('judge/applied.json','w'),ensure_ascii=False)
json.dump(heading,open('judge/heading_kept.json','w'),ensure_ascii=False)
