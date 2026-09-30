"""Local, version-checked workaround for GraySynth numeric phase wrapping.

The installed implementation uses p(angle % pi), which does not preserve
p(angle). Keep the dependency untouched and correct that expression in a local
copy of its function. Exhaustive operator checks are required by the caller.
"""
import inspect
from qiskit.synthesis import synth_cnot_phase_aam


def fixed_aam(cnots,angles,section_size=2):
    source=inspect.getsource(synth_cnot_phase_aam)
    bad='angles[index] % np.pi'
    assert bad in source, 'Dependency changed: re-audit this workaround'
    source=source.replace(bad,'angles[index] % (2 * np.pi)')
    namespace=dict(synth_cnot_phase_aam.__globals__)
    exec(compile(source,'<local_aam_phase_wrap_fix>','exec'),namespace)
    return namespace['synth_cnot_phase_aam'](cnots,list(angles),section_size)
