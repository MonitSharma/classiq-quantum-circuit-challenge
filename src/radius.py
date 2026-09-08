from search import *
from formula import *
def radius(y):
 if 11<=y<=27:
  if y in (11,27):return 2
  if y in (12,26):return 4
  if y in (13,14,24,25):return 6
  return 7 # radius 8 handled by extra x=32 and x=48 terms
 if 35<=y<=47:
  if y in (35,47):return 2
  if y in (36,46):return 4
  if y in (37,38,44,45):return 5
  return 6
 return 0
R=[truth(y for y in range(64) if radius(y)>>b&1) for b in range(3)]
if __name__=='__main__':
 for t in R:print('esop',esop(t,6),'and count',cost(formula(t,6)),formula(t,6),flush=True)
 from xag import Graph
 g=Graph();roots=[g.expr(remap(formula(t,6),range(6,12))) for t in R]
 print('graph AND',len(g.nodes),'root',roots,'ancestor',len(g.ancestors(roots)))
 # Write three-output ESOP for ABC minimization.
 Path('experiments/radius.pla').write_text('.i 6\n.o 3\n'+''.join(''.join(str((y>>b)&1) for b in range(6))+' '+''.join(str((radius(y)>>b)&1) for b in range(3))+'\n' for y in range(64))+'.e\n')
