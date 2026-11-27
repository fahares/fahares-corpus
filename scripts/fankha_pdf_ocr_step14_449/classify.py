import json,random
from collections import Counter
cP=Counter(); cT=Counter(); C=[]
for v in range(1,35):
    d=json.load(open(f'pairs_{v:02d}.json')); cP.update(d['pdfcnt']); cT.update(d['txtcnt']); C+=d['cands']
def cls(x):
    t,p=x['t'],x['p']
    if sorted(t)==sorted(p): return 'anagram'
    if cT[p]>=2 and cP[p]>=2: return 'ocr'      # print word is a real word: take PDF
    if cT[p]==0 and cT[t]>=3: return 'keep'     # print form never in clean text: typo or PDF artifact
    return 'review'
for x in C: x['cls']=cls(x); x['cT_t']=cT[x['t']]; x['cT_p']=cT[x['p']]; x['cP_t']=cP[x['t']]; x['cP_p']=cP[x['p']]
json.dump(C,open('classified.json','w'),ensure_ascii=False)
print(Counter(x['cls'] for x in C))
random.seed(5)
for k in ('ocr','keep','review'):
    print('==',k)
    for x in random.sample([y for y in C if y['cls']==k],12): print(x['vol'],x['page'],x['traw'],'|',x['praw'],x['cT_t'],x['cT_p'])
