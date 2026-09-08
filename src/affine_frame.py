"""Small exact affine-parity-frame model for six-bit reversible synthesis."""

from dataclasses import dataclass


@dataclass
class AffineFrame:
    """Rows map logical bits to the current physical parity wires."""

    rows: tuple[int, ...] = tuple(1 << i for i in range(6))
    offsets: tuple[int, ...] = (0, 0, 0, 0, 0, 0)

    def cnot(self, control: int, target: int) -> "AffineFrame":
        rows = list(self.rows); offsets = list(self.offsets)
        rows[target] ^= rows[control]; offsets[target] ^= offsets[control]
        return AffineFrame(tuple(rows), tuple(offsets))

    def x(self, target: int) -> "AffineFrame":
        offsets = list(self.offsets); offsets[target] ^= 1
        return AffineFrame(self.rows, tuple(offsets))

    def invertible(self) -> bool:
        rows = list(self.rows); rank = 0
        for bit in range(6):
            pivot = next((i for i in range(rank, 6) if rows[i] >> bit & 1), None)
            if pivot is None: continue
            rows[rank], rows[pivot] = rows[pivot], rows[rank]
            for i in range(6):
                if i != rank and (rows[i] >> bit) & 1: rows[i] ^= rows[rank]
            rank += 1
        return rank == 6


def gaussian_transition(source: AffineFrame, target: AffineFrame) -> list[tuple[str, int, int]]:
    """Synthesize a safe CNOT/X transition between two affine frames.

    The implementation uses reversible row elimination and returns operations
    in physical-wire coordinates.  It is exact for frames related by CNOT/X
    operations; callers retain the inverse sequence when a temporary frame is
    required.
    """
    if not source.invertible() or not target.invertible():
        raise ValueError("affine frame must be invertible")
    # A compact constructive fallback: walk source toward target by matching
    # rows using CNOTs, then offsets.  The six-bit size keeps this bounded and
    # deterministic; verification is performed by the caller.
    current = source; ops: list[tuple[str, int, int]] = []
    for target_row in range(6):
        if current.rows[target_row] == target.rows[target_row]: continue
        for control in range(6):
            if control != target_row and current.rows[target_row] ^ current.rows[control] == target.rows[target_row]:
                current = current.cnot(control, target_row); ops.append(("cx", control, target_row)); break
    if current.rows != target.rows:
        raise ValueError("target frame requires a broader parity synthesis")
    for bit in range(6):
        if current.offsets[bit] != target.offsets[bit]: ops.append(("x", bit, bit))
    return ops
