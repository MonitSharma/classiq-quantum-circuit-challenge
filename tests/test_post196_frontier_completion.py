"""The actual row-code counterexample must not omit free-cell assignments."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from post196_code_frontier import cells_of,supports_and_separations,complete,completion_subsets
from two_stage_oracle import ROWCLS

def test_real_row_completion_includes_lower_support_solution():
 order,members=cells_of(ROWCLS,32)
 support,sep,pairs=supports_and_separations(order,members)
 a,b=6385,4710;full=(1<<len(pairs))-1
 options,free=complete(full&~(int(sep[a])|int(sep[b])),pairs,len(order))
 assert min(support[c] for c in options)==43
 candidates=list(completion_subsets(options,free))
 assert min(support[c] for c in candidates)==40
 assert all((int(sep[a])|int(sep[b])|int(sep[c]))==full for c in candidates)
