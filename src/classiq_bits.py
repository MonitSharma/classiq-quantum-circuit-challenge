import sys, json, re, os
from pathlib import Path
import classiq
from classiq import *
from classiq.qmod.symbolic import pi
from classiq.interface.generator.hardware.hardware_data import CustomHardwareSettings
from search import nested_terms,row_terms,esop
from formula import formula
from qiskit import qasm2,transpile as qiskit_transpile

def expression(t,v):
 cubes=[]
 for m,value in esop(t,6):
  cubes.append(f'(({v} & {m}) == {value})' if m else '(True)')
 return '('+' ^ '.join(cubes)+')' if cubes else '(False)'

def fexpr(e,v):
 if isinstance(e,int):return str(bool(e))
 if e[0]=='v':return f'({v}[{e[1]}] == 1)'
 if e[0]=='not':return f'({fexpr(e[1],v)} == False)'
 op=' & ' if e[0]=='and' else ' ^ '
 return '('+fexpr(e[1],v)+op+fexpr(e[2],v)+')'

def generate(name):
 if name.startswith('rank'):terms=json.loads(Path('artifacts/rank_terms.json').read_text())
 elif name.startswith('rows'):terms=row_terms()
 else:terms=nested_terms()
 ex=fexpr if 'formula' in name else expression
 def expr(t,v):return fexpr(formula(t,6),v) if 'formula' in name else expression(t,v)
 conditions=[f'({expr(x,"x")} & {expr(y,"y")})' for x,y in terms]
 lines=['@qperm','def logo_phase_oracle(x: Const[QArray[QBit]], y: Const[QArray[QBit]]) -> None:']
 if 'whole' in name:lines.append('    control('+' ^ '.join(conditions)+', lambda: phase(pi))')
 else:
  for c in conditions:lines.append(f'    control({c}, lambda: phase(pi))')
 lines+=['','@qfunc','def main(x: Output[QArray[QBit,6]], y: Output[QArray[QBit,6]]) -> None:', '    allocate(6,x)','    allocate(6,y)','    hadamard_transform(x)','    hadamard_transform(y)','    logo_phase_oracle(x,y)']
 code='\n'.join(lines)
 Path('experiments/'+name+'.py').write_text('from classiq import *\nfrom classiq.qmod.symbolic import pi\n'+code+'\n')
 scope=globals().copy();exec(compile(code,name,'exec'),scope)
 model=create_model(scope['main'],constraints=Constraints(optimization_parameter=OptimizationParameter.DEPTH,max_width=18))
 write_qmod(model,'artifacts/'+name)
 return model

if __name__=='__main__':
 name=sys.argv[1] if len(sys.argv)>1 else 'nested_bits_formula'
 model=generate(name)
 if '--model-only' in sys.argv:sys.exit()
 qp=synthesize(model)
 raw=export(qp,TargetLanguage.QASM2);Path('artifacts/'+name+'_raw.qasm').write_text(raw)
 lines=raw.splitlines();idx=[i for i,l in enumerate(lines) if l.lstrip().startswith('hadamard_transform_') and 'q[' in l]
 if len(idx)!=2:raise ValueError('Expected exactly two preparation calls')
 source='\n'.join(l for i,l in enumerate(lines) if i not in idx)
 q=qasm2.loads(source,custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
 q=qiskit_transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
 Path('artifacts/'+name+'.qasm').write_text(qasm2.dumps(q))
 print(name,'depth',q.depth(),'cx',q.count_ops().get('cx'),flush=True)
