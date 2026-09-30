"""mkqmod.py in.qasm out.qmod : literal gate-for-gate QMOD companion (same format as the cx568 artifact)."""
import sys, re, hashlib
src = open(sys.argv[1]).read(); sha = hashlib.sha256(src.encode()).hexdigest()
L = [f'// Standalone QASM SHA-256: {sha}',
     '// Literal gate-for-gate companion of the QASM; main adds twelve preparation Hadamards (absent from the QASM).',
     'qfunc conditional_loader_logo_oracle(q: qbit[18]) {']
for line in src.splitlines():
    line = line.strip()
    if line.startswith('cx '):
        a, b = re.findall(r'q\[(\d+)\]', line); L.append(f'  CX(q[{a}], q[{b}]);')
    elif line.startswith('u3('):
        ps = line[line.index('(') + 1:line.index(')')].split(','); q = re.findall(r'q\[(\d+)\]', line)[0]
        L.append(f'  U({ps[0]}, {ps[1]}, {ps[2]}, 0.0, q[{q}]);')
L += ['}', '', 'qfunc main(output q: qbit[18]) {', '  allocate(18, q);'] + [f'  H(q[{i}]);' for i in range(12)] + ['  conditional_loader_logo_oracle(q);', '}']
open(sys.argv[2], 'w').write('\n'.join(L) + '\n')
