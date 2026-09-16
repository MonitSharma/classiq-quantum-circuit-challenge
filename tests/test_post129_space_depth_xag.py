import tempfile
import unittest
from pathlib import Path

from post129_pebble import solve
from post129_space_depth_xag import audit


class Post129Tests(unittest.TestCase):
    def test_exact_inventory_metrics_for_toy_xag(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "toy.xag"
            path.write_text("AND 2 4\nOUTPUT 16\n")
            row = audit(path)
            self.assertTrue(row["exact_logo"] is False)
            self.assertEqual(row["and_count"], 1)
            self.assertEqual(row["multiplicative_depth"], 1)

    def test_six_pebble_solver_simple_root(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "toy.xag"
            path.write_text("AND 2 4\nOUTPUT 8192\n")
            result = solve(path, max_states=1000)
            self.assertEqual(result["status"], "SAT")
            self.assertEqual(result["toggle_count"], 2)


if __name__ == "__main__":
    unittest.main()
