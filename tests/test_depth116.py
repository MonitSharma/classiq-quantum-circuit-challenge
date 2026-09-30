"""Guard the new reachable-code phase freedom and the resulting oracle."""
from pathlib import Path
import hashlib
import sys

import numpy as np
from classiq_synth.core.verify import exhaustive_verify

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/post151_sa'))


def test_new_phase_representation_matches_every_reachable_code():
    from kgenco import build_F, CH, check
    coefficients = np.load(ROOT / 'artifacts/116/recipes/kernel_co.npy') / np.pi
    _, known = build_F()
    assert np.count_nonzero(known) == 182
    assert np.count_nonzero(coefficients) == 63
    # Compare directly with the class-code truth table, not just the old recipe.
    assert check(coefficients) < 1e-12


def test_depth116_artifact_and_exhaustive_oracle():
    qasm = ROOT / 'artifacts/116/conditional_loader_116.qasm'
    assert hashlib.sha256(qasm.read_bytes()).hexdigest() == (
        '5f4e4162dc0880a11db275cb94b573a38f398f3b975c9fec55d7a2652872a570')
    report = exhaustive_verify(qasm, write_report=False)
    assert (report['depth'], report['cx_count'], report['width']) == (116, 573, 18)
    assert report['basis_inputs_checked'] == 4096
    assert report['max_error'] < 1e-12
    assert report['ancilla_error'] < 1e-12


def test_saved_recipe_replays_verified_116(tmp_path):
    from replay116 import replay
    output = tmp_path / 'replay.qasm'
    replay(output)
    report = exhaustive_verify(output, write_report=False)
    assert (report['depth'], report['cx_count'], report['width']) == (116, 573, 18)
    assert report['max_error'] < 1e-12


def test_cx571_variant_and_recipe(tmp_path):
    from replay571 import replay
    qasm=ROOT/'artifacts/116/conditional_loader_116_cx571.qasm'
    assert hashlib.sha256(qasm.read_bytes()).hexdigest()==(
        '8e50e43b06cb11e24cfbea52a4d74606ac9000aea957755bdb8bb1a08a4029a1')
    for path in (qasm,tmp_path/'replay571.qasm'):
        if path!=qasm:
            replay(path)
        report=exhaustive_verify(path,write_report=False)
        assert (report['depth'],report['cx_count'],report['width'])==(116,571,18)
        assert report['basis_inputs_checked']==4096
        assert report['max_error']<1e-12


def test_cx565_champion_artifact():
    qasm = ROOT / 'artifacts/116/conditional_loader_116_cx565.qasm'
    assert hashlib.sha256(qasm.read_bytes()).hexdigest() == (
        '7f73d2c10d9c1454041e4aa6b1043985999f06f3acc5fe69c6b553e22d157156')
    report = exhaustive_verify(qasm, write_report=False)
    assert (report['depth'], report['cx_count'], report['width']) == (116, 565, 18)
    assert report['basis_inputs_checked'] == 4096
    assert report['max_error'] < 1e-12
    assert report['ancilla_error'] < 1e-12
