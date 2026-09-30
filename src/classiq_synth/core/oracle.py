"""Ground-truth geometric oracle specification for the Classiq Challenge."""

import numpy as np


def logo(x: int, y: int) -> bool:
    """Classiq challenge target geometric predicate: true if (x, y) is inside the logo."""
    return bool(
        (2 <= x <= 26 and 29 <= y <= 53)
        or (26 <= x <= 49 and 39 <= y <= 43)
        or ((x - 55) ** 2 + (y - 41) ** 2 <= 42)
        or ((x - 40) ** 2 + (y - 19) ** 2 <= 72)
    )


# 64x64 Boolean mask
MASK = np.array([[logo(x, y) for x in range(64)] for y in range(64)], dtype=np.uint8)


def get_target_array() -> np.ndarray:
    """Return the expected phase array (-1 for logo point, +1 otherwise) for all 4096 inputs."""
    return np.array([-1 if logo(x, y) else 1 for y in range(64) for x in range(64)], dtype=np.int32)
