import json,random
from collections import Counter
C=json.load(open('classified.json'))
def strict(x):
    t,p=x['t'],x['p']
    if t.startswith(p) or t.endswith(p) or p.startswith(t) or p.endswith(t): return False
    if x['dist']==1: return x['sup']>=1
    return len(t)>=5 and x['sup']>=2
def cls(x):
    if not strict(x): return 'loose'
    t,p=x['t'],x['p']
    if sorted(t)==sorted(p): return 'anagram'
    if x['cT_p']>=2 and x['cP_p']>=2: return 'ocr'
    if x['cT_p']==0 and x['cT_t']>=3: return 'keep'
    return 'review'
for x in C: x['cls2']=cls(x)
json.dump(C,open('classified2.json','w'),ensure_ascii=False)
print(Counter(x['cls2'] for x in C))
random.seed(11)
for k in ('ocr','keep','review','anagram'):
    print('==',k)
    for x in random.sample([y for y in C if y['cls2']==k],14): print(x['vol'],x['page'],x['traw'],'|',x['praw'],x['cT_t'],x['cT_p'],x['dist'],x['sup'])
