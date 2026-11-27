import re, json, unicodedata, pymupdf
D=pymupdf.open('/home/tabib/projects/apps/fahares-sources/fankha/pdf/fankha-labeled.pdf')
LABS=json.load(open('/tmp/claude-1000/-home-tabib--claude-account2-spares-spare-hNrd2Y/81059129-e70e-4637-8044-57d1d5df863a/scratchpad/labels.json'))
LTR=re.compile(r'^[0-9۰-۹٠-٩A-Za-zāīūčšžġḥṣḍṭẓʿ’‘\-\./\*×:()\[\],]+$')
STRONG=re.compile(r'[0-9۰-۹٠-٩A-Za-z]')
def page_lines(i):
    p=D[i]; mid=p.rect.width/2
    W=[(w[0],w[1],w[2],w[3],unicodedata.normalize('NFKC',w[4])) for w in p.get_text('words')]
    # column detection: if many words fully on each side, two columns
    left=[w for w in W if w[2]<mid+5]; right=[w for w in W if w[0]>mid-5]
    two = len(left)>40 and len(right)>40 and sum(1 for w in W if w[0]<mid-5<mid+5<w[2])<0.1*len(W)
    cols=[right,left] if two else [W]
    out=[]
    for C in cols:
        C=sorted(C,key=lambda w:(w[1]+w[3])/2)
        lines=[]
        for w in C:
            yc=(w[1]+w[3])/2
            if lines and abs(lines[-1][0]-yc)<3: lines[-1][1].append(w)
            else: lines.append([yc,[w]])
        for yc,ws in lines:
            ws.sort(key=lambda w:-w[2])
            toks=[w[4] for w in ws]
            # reverse runs of LTR tokens (containing a strong LTR char)
            res=[];run=[]
            for t in toks:
                if LTR.match(t) and STRONG.search(t): run.append(t)
                else:
                    res+=run[::-1]; run=[]; res.append(t)
            res+=run[::-1]
            out.append(' '.join(res))
    return out
