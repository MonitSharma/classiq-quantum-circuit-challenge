"""Enumerate affine realizations of fixed NIST representatives, then merge.

Witnesses are checked on every input. AND count is only a screen; retained
variants must subsequently be evaluated by the semantic register compiler.
"""
import argparse,itertools,json,re,random,time
from pathlib import Path
from post190_semantic_register import INPUTS,FULL,pivots,contains,eval_form
from post190_xag_inplace_lower import outputs
from post190_degree_rank_bound import targets


def mappings(t,r,limit=200000,count=24):
    phase=[[sum(1<<v for v in range(128) if (((v&63)&u).bit_count()^(v>>6))&1==s) for s in range(2)] for u in range(64)]
    nodes=0;found=0
    def rec(images,allowed,c):
        nonlocal nodes
        nodes+=1
        if nodes>limit:return
        n=len(images)
        if n==64:
            yield images,allowed,c;return
        for v in range(1,64):
            if v in images:continue
            new=[x^v for x in images];ok=allowed
            for i,x in enumerate(new,n):
                a,b=t[i],r[x^c]
                if abs(a)!=abs(b):ok=0;break
                if a:ok &=phase[i][int((a<0)!=(b<0))]
                if not ok:break
            if ok:yield from rec(images+new,ok,c)
            if nodes>limit:return
    for c in range(64):
        if abs(t[0])!=abs(r[c]):continue
        allowed=(1<<128)-1
        if t[0]:allowed&=phase[0][int((t[0]<0)!=(r[c]<0))]
        for images,allowed,c in rec([0],allowed,c):
            cols=[images[1<<i] for i in range(6)]
            inv={sum(((col&x).bit_count()%2)<<i for i,col in enumerate(cols)):x for x in range(64)}
            assert len(inv)==64
            while allowed:
                bit=allowed&-allowed;allowed^=bit;v=bit.bit_length()-1
                yield dict(input_map=[inv[x^(v&63)] for x in range(64)],output_linear_on_rep=c,output_constant=v>>6)
                found+=1
                if found>=count:return
        if nodes>limit:return


def instantiate(source,mapping):
    lines=source.splitlines();top=[re.search(r'= \((.*?)\) \* \((.*?)\)',l).groups() for l in lines if re.match(r'a\d+ =',l)]
    def aff(expr):
        c=0;mask=0;nodes=[]
        for token in expr.split('+'):
            if token=='1':c^=1
            elif token.startswith('x'):mask^=1<<(int(token[1:])-1)
            elif token.startswith('a'):nodes.append(6+int(token[1:]))
        vals=[c^((mask&x).bit_count()%2) for x in mapping['input_map']]
        const=vals[0];indices=[i for i in range(6) if vals[1<<i]^const]
        assert all(vals[x]==const^(sum(x>>i&1 for i in indices)%2) for x in range(64))
        return (indices+nodes,bool(const))
    gates=[dict(a=aff(a),b=aff(b)) for a,b in top]
    a,c=aff(lines[-1].split('=')[1].strip());mask=mapping['output_linear_on_rep']
    vals=[(mask&x).bit_count()%2 for x in mapping['input_map']];c^=bool(vals[0]^mapping['output_constant'])
    for i in range(6):
        if vals[1<<i]^vals[0]:
            if i in a:a.remove(i)
            else:a.append(i)
    return dict(k=len(gates),gates=gates,outs=[(a,c)])


def merge(ws):
    signals=[FULL,*INPUTS];gates=[];out=[]
    def resolve(v):
        p={}
        for i,t in enumerate(signals):
            mask=1<<i
            while t:
                b=t.bit_length()-1
                if b in p:t^=p[b][0];mask^=p[b][1]
                else:p[b]=(t,mask);break
        mask=0
        while v:
            b=v.bit_length()-1
            if b not in p:return None
            v^=p[b][0];mask^=p[b][1]
        return ([i-1 for i in range(1,len(signals)) if mask>>i&1],bool(mask&1))
    for w in ws:
        local=list(INPUTS)
        for g in w['gates']:
            a,b=eval_form(g['a'],local),eval_form(g['b'],local);v=a&b
            if resolve(v) is None:gates.append(dict(a=resolve(a),b=resolve(b)));signals.append(v)
            local.append(v)
        out.append(resolve(eval_form(w['outs'][0],local)))
    return dict(k=len(gates),gates=gates,outs=out)


def run(out,count=24,trials=1000):
    assert not out.exists();out.mkdir(parents=True)
    root=Path('artifacts/post190_nist_catalog');data=json.loads((root/'matches.json').read_text());chosen=json.loads((root/'affine_maps.json').read_text());banks={};meta={};tables=targets()
    for key in sorted(chosen):
        target=data[key];rep=next(c for c in target['candidates'] if c['index']==chosen[key]['representative']);source=(root/(key+'_source.slp')).read_text();bank=[];seen=set();metadata=[]
        for m in itertools.chain([chosen[key]],mappings(target['walsh'],rep['walsh'],count=count)):
            w=instantiate(source,m);assert all(outputs(w,x)==[tables[key[0]][int(key[1])][x]] for x in range(64))
            token=json.dumps(w,sort_keys=True)
            if token not in seen:seen.add(token);bank.append(w);metadata.append(m)
        banks[key]=bank;meta[key]=metadata;print('variants',key,len(bank),flush=True)
    (out/'variants.json').write_text(json.dumps(banks));(out/'affine_metadata.json').write_text(json.dumps(meta))
    rng=random.Random(190915);summary={}
    for side in ['x','y']:
        best=100;retained=[];seen=set()
        choices=[banks[side+str(i)] for i in range(3)]
        triples=[(0,0,0)]+[tuple(rng.randrange(len(c)) for c in choices) for _ in range(trials)]
        for indices in triples:
            if indices in seen:continue
            seen.add(indices);w=merge([c[j] for c,j in zip(choices,indices)])
            if w['k']<=best:
                assert all(outputs(w,x)==[t[x] for t in tables[side]] for x in range(64))
                if w['k']<best:best=w['k'];retained=[];print('merged',side,best,indices,flush=True)
                if len(retained)<8:retained.append((indices,w))
        files=[]
        for i,(indices,w) in enumerate(retained):
            fn=f'{side}_candidate_{i}.json';(out/fn).write_text(json.dumps(w,indent=2));files.append(dict(file=fn,indices=indices,and_count=w['k']))
        summary[side]=dict(best_and_count=best,triples_checked=len(seen),candidates=files)
    (out/'report.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--count',type=int,default=24);p.add_argument('--trials',type=int,default=1000);a=p.parse_args();run(a.outdir,a.count,a.trials)
