"""Reproduce the structured class-coordinate and rank-factor facts."""
import argparse, json
from pathlib import Path
from post190_information_space import full_step
from post190_relative_xag import build_reducer, reduce_mod_span
from post190_class_relabel import anf_stats
from two_stage_oracle import ROWCLS, COLCLS, logo

FULL=(1<<64)-1
Y_LABEL=[0,1,2,3,4,5,9,10,11,12,13]
X_LABEL=[0,5,8,9,10,11,12,13,2,3,4]
Y_SEED=[352,63,991,4,480,7,384,983,448,1]
X_SEED=[128,899,1019,16,770,28,384,4,636,32]

def table(values): return sum(int(v)<<i for i,v in enumerate(values))
def rank(rows):
 p={}
 for x in rows:
  while x:
   b=x.bit_length()-1
   if b in p:x^=p[b]
   else:p[b]=x;break
 return len(p)
def cuts(classes): return [table([(m>>classes[t])&1 for t in range(64)]) for m in range(0,2048,2)]
def class_matrix():
 return [[int(logo(next(x for x,c in enumerate(COLCLS) if c==j),next(y for y,c in enumerate(ROWCLS) if c==i))) for j in range(11)] for i in range(11)]
def witness_signals(path, side):
 w=json.loads(Path(path).read_text()); sig=[table([(t>>i)&1 for t in range(64)]) for i in range(6)]; out=[]
 def ev(f):
  value = FULL if f[1] else 0
  for i in f[0]: value ^= sig[i]
  return value
 for g in w['gates']:
  a,b=ev(g['a']),ev(g['b']); out.append(a&b); sig.append(a&b)
 # The protected descriptor includes the side's raw tag alongside its three
 # code bits; include that already-paid input direction in the span.
 sig.append(table([(t >> (5 if side == 'y' else 4)) & 1 for t in range(64)]))
 return [FULL,*sig]
def intersection_dim(a,b): return rank(a)+rank(b)-rank(a+b)
def trajectory_signals(path,index):
 e=json.loads(Path(path).read_text())[index]; v=tuple(int(x,16) for x in e['full_values']); vals=[FULL,*[table([(t>>i)&1 for t in range(64)]) for i in range(6)]]
 for op in e['ops']:
  v=full_step(v,((op[0],tuple(op[1])),)); vals.extend(x&FULL for x in v)
 return vals
def run(out):
 out.mkdir(parents=True,exist_ok=True); Y=cuts(ROWCLS);X=cuts(COLCLS)
 dist={s:{str(d):sum(anf_stats(t)['degree']==d for t in cs) for d in range(7)} for s,cs in [('y',Y),('x',X)]}
 low={s:rank([t for t in cs if anf_stats(t)['degree']<=5]) for s,cs in [('y',Y),('x',X)]}
 ybits=[table([(Y_LABEL[c]>>b)&1 for c in ROWCLS]) for b in range(4)]; xbits=[table([(X_LABEL[c]>>b)&1 for c in COLCLS]) for b in range(4)]
 expected={'y':[hex(x) for x in ybits],'x':[hex(x) for x in xbits], 'y_stats':[anf_stats(x) for x in ybits], 'x_stats':[anf_stats(x) for x in xbits]}
 formula_mismatches=0
 for y in range(64):
  yl=Y_LABEL[ROWCLS[y]]; m=yl&7; f=yl>>3
  for x in range(64):
   xl=X_LABEL[COLCLS[x]]; l=xl&7; g=xl>>3
   formula_mismatches += bool(((f^g) and (m+l>=6)) ^ ((f and g) and (m>=5))) != bool(logo(x,y))
 C=class_matrix(); seed_ok=all(sum(((Y_SEED[i-1]>>(r-1))&1)*((X_SEED[i-1]>>(c-1))&1) for i in range(1,11))%2==C[r][c] for r in range(1,11) for c in range(1,11))
 class_space_y=cuts(ROWCLS)[1:]; class_space_x=cuts(COLCLS)[1:]
 intersections={}
 for side,path,w in [('y','artifacts/post190_nist_variants_wide/y_candidate_0.json',class_space_y),('x','artifacts/post190_nist_variants/x_candidate_0.json',class_space_x)]:
  s=witness_signals(path,side); intersections[side]=intersection_dim(s,w)
 for side,path,idx,w in [('y','artifacts/post190_information_space/quotient_y/frontier.json',0,class_space_y),('x','artifacts/post190_information_space/quotient_x/frontier.json',2,class_space_x)]: intersections[side+'_trajectory']=intersection_dim(trajectory_signals(path,idx),w)
 report={'class_counts':{'rows':len(set(ROWCLS)),'cols':len(set(COLCLS))},'ones':sum(map(sum,C)),'matrix_rank':rank([sum(v<<j for j,v in enumerate(row)) for row in C]),'core_rank':rank([sum(v<<j for j,v in enumerate(row[1:],1)) for row in C[1:]]),'cut_degree_distribution':dist,'degree_le5_span_rank':low,'structured_targets':expected,'structured_formula_mismatches':formula_mismatches,'rank10_seed_verified':seed_ok,'witness_class_cut_intersections':intersections}
 (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('artifacts/post190_structured_audit'));run(p.parse_args().out)
