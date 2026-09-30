# Use the project virtual environment when it exists, otherwise the system interpreter.
PYTHON ?= $(shell test -x .venv/bin/python && echo .venv/bin/python || echo python3)
PYTEST ?= $(PYTHON) -m pytest
VERIFY  = OPENBLAS_NUM_THREADS=1 $(PYTHON) src/exhaustive_verify.py

BEST = artifacts/111/conditional_loader_111_cx557.qasm

.PHONY: help verify-best verify-all results figures verify verify-111 verify-111-557 verify-111-558 verify-111-561 \
        verify-112 verify-112-573 verify-112-576 \
        verify-113 verify-113-564 verify-113-568 \
        verify-114-564 verify-114-571 \
        verify-115 verify-115-566 verify-115-567 verify-115-568 \
        verify-115-569 verify-115-571 verify-565 verify-570 verify-571 verify-dense verify-submission \
        verify-cx test build-c clean

help:
	@echo "make verify-best        exhaustive check of the best circuit (numpy only)"
	@echo "make verify-all         exhaustive check of every depth-111, depth-112, depth-113, depth-114, depth-115 and depth-116 circuit (numpy only)"
	@echo "make results            re-verify all milestones and rebuild results/verified_circuits.csv"
	@echo "make figures            regenerate docs/figures/*.png"
	@echo "make verify-111         exhaustive check of the 111/557 champion circuit with the Qiskit-based verifier"
	@echo "make verify-111-557     exhaustive check of the 111/557 circuit with the Qiskit-based verifier"
	@echo "make verify-111-558     exhaustive check of the 111/558 circuit with the Qiskit-based verifier"
	@echo "make verify-111-561     exhaustive check of the 111/561 circuit with the Qiskit-based verifier"
	@echo "make verify-112         exhaustive check of the 112/573 circuit with the Qiskit-based verifier"
	@echo "make verify-112-573     exhaustive check of the 112/573 circuit with the Qiskit-based verifier"
	@echo "make verify-112-576     exhaustive check of the 112/576 circuit with the Qiskit-based verifier"
	@echo "make verify-113         exhaustive check of the 113/564 best circuit with the Qiskit-based verifier"
	@echo "make verify-113-564     exhaustive check of the 113/564 circuit with the Qiskit-based verifier"
	@echo "make verify-113-568     exhaustive check of the 113/568 circuit with the Qiskit-based verifier"
	@echo "make verify-114-564     exhaustive check of the 114/564 circuit with the Qiskit-based verifier"
	@echo "make verify-114-571     exhaustive check of the 114/571 circuit with the Qiskit-based verifier"
	@echo "make verify-115-566     exhaustive check of the 115/566 circuit with the Qiskit-based verifier"
	@echo "make verify-115-567     exhaustive check of the 567-CX circuit with the Qiskit-based verifier"
	@echo "make verify-submission  exhaustive check of submission/submission.qasm"
	@echo "make verify-dense       dense random-state check (Qiskit Aer)"
	@echo "make test               run the test suite"
	@echo "make build-c            compile the C beam searches in src/post151_sa/c/"
	@echo "make clean              remove Python caches"

verify-best:
	$(PYTHON) scripts/verify_circuit.py $(BEST)

verify-all:
	$(PYTHON) scripts/verify_circuit.py artifacts/111/*.qasm artifacts/112/*.qasm artifacts/113/*.qasm artifacts/114/*.qasm artifacts/115/*.qasm artifacts/116/*.qasm

results:
	$(PYTHON) scripts/collect_results.py --verify

figures:
	$(PYTHON) scripts/make_figures.py

verify: verify-submission

verify-submission:
	$(VERIFY) submission/submission.qasm

verify-111: verify-111-557

verify-111-557:
	$(VERIFY) artifacts/111/conditional_loader_111_cx557.qasm

verify-111-558:
	$(VERIFY) artifacts/111/conditional_loader_111_cx558.qasm

verify-111-561:
	$(VERIFY) artifacts/111/conditional_loader_111_cx561.qasm

verify-112: verify-112-573

verify-112-573:
	$(VERIFY) artifacts/112/conditional_loader_112_cx573.qasm

verify-112-576:
	$(VERIFY) artifacts/112/conditional_loader_112_cx576.qasm

verify-113: verify-113-564

verify-113-564:
	$(VERIFY) artifacts/113/conditional_loader_113_cx564.qasm

verify-113-568:
	$(VERIFY) artifacts/113/conditional_loader_113_cx568.qasm

verify-114-564:
	$(VERIFY) artifacts/114/conditional_loader_114_cx564.qasm

verify-114-571:
	$(VERIFY) artifacts/114/conditional_loader_114_cx571.qasm

verify-115:
	$(VERIFY) artifacts/115/conditional_loader_115.qasm

verify-115-566:
	$(VERIFY) artifacts/115/conditional_loader_115_cx566.qasm

verify-115-567:
	$(VERIFY) artifacts/115/conditional_loader_115_cx567.qasm

verify-115-568:
	$(VERIFY) artifacts/115/conditional_loader_115_cx568.qasm

verify-115-569:
	$(VERIFY) artifacts/115/conditional_loader_115_cx569.qasm

verify-115-571:
	$(VERIFY) artifacts/115/conditional_loader_115_cx571.qasm

verify-565:
	$(VERIFY) artifacts/116/conditional_loader_116_cx565.qasm

verify-570:
	$(VERIFY) artifacts/116/conditional_loader_116_cx570.qasm

verify-571:
	$(VERIFY) artifacts/116/conditional_loader_116_cx571.qasm

verify-cx:
	$(VERIFY) artifacts/118b/conditional_loader_118b.qasm

verify-dense:
	OPENBLAS_NUM_THREADS=1 $(PYTHON) src/verify.py submission/submission.qasm 5

test:
	$(PYTEST) tests/test_champion.py tests/test_core_verifier.py tests/test_depth116.py tests/test_kernel128.py \
	          tests/test_parity_search.py tests/test_typed_restore_bound.py tests/test_depth115_deadlines.py \
	          tests/test_verify_circuit.py tests/test_tail_sat_encoding.py -v

build-c:
	$(MAKE) -C src/post151_sa/c all

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
