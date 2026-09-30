import pytest
"""Automated tests validating the Classiq Challenge Depth 116 champion deliverables."""

from pathlib import Path
from classiq_synth.core.circuit import load_circuit, get_circuit_metrics
from classiq_synth.core.verify import exhaustive_verify

ROOT = Path(__file__).resolve().parents[1]
CHAMPION_111_557_SHA = "339c99e90a56a2aff4e7ce3f465879cd4a25acc8a1f82acb78a4534cd8108b1a"
CHAMPION_111_558_SHA = "6eb6fc286ba764787c170ddeec324e60f45bfaa7e7a9f7051f5e69b4d3ea4fe6"
CHAMPION_111_561_SHA = "7fb5dcb9227dfe71d7b87f0cd29bdd7bda1fb10537c09b227ff953bdde2d4314"
CHAMPION_112_573_SHA = "a24fc374370e6ea6f0242dd49f596ac82d6cdf41347dbffe57a3e4adb48d2326"
CHAMPION_112_576_SHA = "c770a17334ecd70df024e6377063b5d335f3e2a0811a2ebf320a461f50a95f64"
CHAMPION_113_564_SHA = "6cf736a40af57d503641887dc73c04a9a8278811ec11ad55e87d2a9c51d32ccb"
CHAMPION_113_568_SHA = "73fbd06c16b609764eb51c8e5aede8c262b612d2764558da5479477eef20e668"
CHAMPION_114_564_SHA = "1bf3025720ef60e2a74e18ae3c77d91c8339dd82e2058805b2b458d7fcc73eab"
CHAMPION_114_571_SHA = "7510ebd22c237d7948ed52e3af57369a4378100a6e81048e20459051b1bb3aa9"
CHAMPION_115_SHA = "d61f2344fdc86eda504dfd86c39f4eb4a4887c0ff18e46238a9799c2a5dbe3ce"
CHAMPION_115_566_SHA = "3573dfc6cbda537d4a0d17df9935773d93ccd239dac5a2c01ab1d83fc11ccc2e"
CHAMPION_115_567_SHA = "8101000e89e5d0ca4c2dcffeb751fdc5c1dfe2ed4af2155d14064068ebecba69"
CHAMPION_115_568_SHA = "ec51775f582487f6eac78dee5f23133211efc5ec0a195f24ca4377e22deabfa3"
CHAMPION_115_569_SHA = "0664dc07168b96a919b978856d6593b9631a6a16dca90fcf24bc94b07adaeca2"
CHAMPION_115_571_SHA = "49a699d8b9898baa0531fc6c87aa214483613ea10f45e9086d8e9c11dc7c423e"
CHAMPION_116_565_SHA = "7f73d2c10d9c1454041e4aa6b1043985999f06f3acc5fe69c6b553e22d157156"
TIEBREAK_116_570_SHA = "4710d2b9a4312bc658e3041b34dd48e2b434c7e188ab27bd563640ed67c57c65"
TIEBREAK_116_571_SHA = "8e50e43b06cb11e24cfbea52a4d74606ac9000aea957755bdb8bb1a08a4029a1"
BASELINE_116_573_SHA = "5f4e4162dc0880a11db275cb94b573a38f398f3b975c9fec55d7a2652872a570"
OPTIMAL_117_SHA = "8ce115b11b716f3153c042e9d8c8a109deb468ae6888f73007b2e259535d2bd4"
TIEBREAK_117_SHA = "d26fa5c655b05c8a9f7f4fc93002061045acaef0368d12f19f7318d6be01c11e"
BASELINE_117_SHA = "40cafa773e9afb4f679897a298466d58d3b7bfa6698fff90e94763e85f07a2da"


@pytest.mark.parametrize("name,cx,sha", [
    ("conditional_loader_111_cx557.qasm", 557, CHAMPION_111_557_SHA),
    ("conditional_loader_111_cx558.qasm", 558, CHAMPION_111_558_SHA),
    ("conditional_loader_111_cx561.qasm", 561, CHAMPION_111_561_SHA),
])
def test_champion_111_metrics(name, cx, sha):
    """Verify that the artifacts/111 circuits achieve depth 111, stated CX count, and 18 qubits."""
    metrics = get_circuit_metrics(ROOT / "artifacts" / "111" / name)
    assert metrics["depth"] == 111, f"Expected depth 111, got {metrics['depth']}"
    assert metrics["cx_count"] == cx, f"Expected {cx} CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == sha, f"SHA mismatch: {metrics['sha256']}"


@pytest.mark.parametrize("name,cx,sha", [
    ("conditional_loader_112_cx573.qasm", 573, CHAMPION_112_573_SHA),
    ("conditional_loader_112_cx576.qasm", 576, CHAMPION_112_576_SHA),
])
def test_champion_112_metrics(name, cx, sha):
    """Verify that the artifacts/112 circuits achieve depth 112, stated CX count, and 18 qubits."""
    metrics = get_circuit_metrics(ROOT / "artifacts" / "112" / name)
    assert metrics["depth"] == 112, f"Expected depth 112, got {metrics['depth']}"
    assert metrics["cx_count"] == cx, f"Expected {cx} CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == sha, f"SHA mismatch: {metrics['sha256']}"


@pytest.mark.parametrize("name,cx,sha", [
    ("conditional_loader_113_cx564.qasm", 564, CHAMPION_113_564_SHA),
    ("conditional_loader_113_cx568.qasm", 568, CHAMPION_113_568_SHA),
])
def test_champion_113_metrics(name, cx, sha):
    """Verify that the artifacts/113 circuits achieve depth 113, stated CX count, and 18 qubits."""
    metrics = get_circuit_metrics(ROOT / "artifacts" / "113" / name)
    assert metrics["depth"] == 113, f"Expected depth 113, got {metrics['depth']}"
    assert metrics["cx_count"] == cx, f"Expected {cx} CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == sha, f"SHA mismatch: {metrics['sha256']}"


@pytest.mark.parametrize("name,cx,sha", [
    ("conditional_loader_114_cx564.qasm", 564, CHAMPION_114_564_SHA),
    ("conditional_loader_114_cx571.qasm", 571, CHAMPION_114_571_SHA),
])
def test_champion_114_metrics(name, cx, sha):
    """Verify that the artifacts/114 circuits have depth 114, the stated CX count, 18 qubits and the recorded SHA."""
    metrics = get_circuit_metrics(ROOT / "artifacts" / "114" / name)
    assert metrics["depth"] == 114, f"Expected depth 114, got {metrics['depth']}"
    assert metrics["cx_count"] == cx, f"Expected {cx} CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == sha, f"SHA mismatch: {metrics['sha256']}"


def test_champion_115_metrics():
    """Verify that artifacts/115 achieves depth 115, 575 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "115" / "conditional_loader_115.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 115, f"Expected depth 115, got {metrics['depth']}"
    assert metrics["cx_count"] == 575, f"Expected 575 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == CHAMPION_115_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_champion_115_566_metrics():
    """Verify that artifacts/115 cx566 achieves depth 115, 566 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "115" / "conditional_loader_115_cx566.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 115, f"Expected depth 115, got {metrics['depth']}"
    assert metrics["cx_count"] == 566, f"Expected 566 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == CHAMPION_115_566_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_champion_115_567_metrics():
    """Verify that artifacts/115 cx567 achieves depth 115, 567 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "115" / "conditional_loader_115_cx567.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 115, f"Expected depth 115, got {metrics['depth']}"
    assert metrics["cx_count"] == 567, f"Expected 567 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == CHAMPION_115_567_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_champion_115_568_metrics():
    """Verify that artifacts/115 cx568 achieves depth 115, 568 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "115" / "conditional_loader_115_cx568.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 115, f"Expected depth 115, got {metrics['depth']}"
    assert metrics["cx_count"] == 568, f"Expected 568 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == CHAMPION_115_568_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_champion_115_569_metrics():
    """Verify that artifacts/115 cx569 achieves depth 115, 569 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "115" / "conditional_loader_115_cx569.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 115, f"Expected depth 115, got {metrics['depth']}"
    assert metrics["cx_count"] == 569, f"Expected 569 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == CHAMPION_115_569_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_champion_115_571_metrics():
    """Verify that artifacts/115 cx571 achieves depth 115, 571 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "115" / "conditional_loader_115_cx571.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 115, f"Expected depth 115, got {metrics['depth']}"
    assert metrics["cx_count"] == 571, f"Expected 571 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == CHAMPION_115_571_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_champion_116_565_metrics():
    """Verify that artifacts/116 cx565 achieves depth 116, 565 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "116" / "conditional_loader_116_cx565.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 116, f"Expected depth 116, got {metrics['depth']}"
    assert metrics["cx_count"] == 565, f"Expected 565 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == CHAMPION_116_565_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_champion_116_570_metrics():
    """Verify that artifacts/116 cx570 achieves depth 116, 570 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "116" / "conditional_loader_116_cx570.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 116, f"Expected depth 116, got {metrics['depth']}"
    assert metrics["cx_count"] == 570, f"Expected 570 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == TIEBREAK_116_570_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_champion_116_571_optimal_metrics():
    """Verify that artifacts/116 cx571 achieves depth 116, 571 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "116" / "conditional_loader_116_cx571.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 116, f"Expected depth 116, got {metrics['depth']}"
    assert metrics["cx_count"] == 571, f"Expected 571 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == TIEBREAK_116_571_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_champion_116_baseline_metrics():
    """Verify that artifacts/116 achieves depth 116, 573 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "116" / "conditional_loader_116.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 116, f"Expected depth 116, got {metrics['depth']}"
    assert metrics["cx_count"] == 573, f"Expected 573 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == BASELINE_116_573_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_champion_optimal_metrics():
    """Verify that artifacts/117 cx576 achieves depth 117, 576 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "117" / "conditional_loader_117_cx576.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 117, f"Expected depth 117, got {metrics['depth']}"
    assert metrics["cx_count"] == 576, f"Expected 576 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == OPTIMAL_117_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_champion_tiebreak_metrics():
    """Verify that artifacts/117 cx577 achieves depth 117, 577 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "117" / "conditional_loader_117_cx577.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 117, f"Expected depth 117, got {metrics['depth']}"
    assert metrics["cx_count"] == 577, f"Expected 577 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == TIEBREAK_117_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_champion_baseline_metrics():
    """Verify that artifacts/117 baseline achieves depth 117, 590 CX gates, and 18 qubits."""
    qasm_path = ROOT / "artifacts" / "117" / "conditional_loader_117.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 117, f"Expected depth 117, got {metrics['depth']}"
    assert metrics["cx_count"] == 590, f"Expected 590 CX, got {metrics['cx_count']}"
    assert metrics["width"] == 18, f"Expected 18 qubits, got {metrics['width']}"
    assert metrics["sha256"] == BASELINE_117_SHA, f"SHA mismatch: {metrics['sha256']}"


def test_submission_matches_champion():
    """Verify that the official submission QASM exactly matches the verified optimal 111 champion."""
    submission_path = ROOT / "submission" / "submission.qasm"
    metrics = get_circuit_metrics(submission_path)

    assert metrics["sha256"] == CHAMPION_111_557_SHA, (
        f"submission.qasm SHA {metrics['sha256']} does not match champion {CHAMPION_111_557_SHA}"
    )
    assert metrics["depth"] == 111
    assert metrics["cx_count"] == 557
    assert metrics["width"] == 18


def test_champion_exhaustive_verification():
    """Run sparse simulation across all 4,096 basis states and check error and zero ancilla leakage."""
    qasm_path = ROOT / "submission" / "submission.qasm"
    report = exhaustive_verify(qasm_path, max_width=18, write_report=False)

    assert report["basis_inputs_checked"] == 4096
    assert report["depth"] == 111
    assert report["cx_count"] == 557
    assert report["width"] == 18
    assert report["max_error"] < 1e-12, f"Excessive coordinate error: {report['max_error']}"
    assert report["ancilla_error"] < 1e-12, f"Ancilla leakage detected: {report['ancilla_error']}"
    assert report["challenge_width_eligible"] is True


def test_118b_metrics():
    """Verify that the 118b CX-optimized milestone achieves depth 118, 585 CX, 18 qubits."""
    qasm_path = ROOT / "artifacts" / "118b" / "conditional_loader_118b.qasm"
    metrics = get_circuit_metrics(qasm_path)

    assert metrics["depth"] == 118
    assert metrics["cx_count"] == 585
    assert metrics["width"] == 18
