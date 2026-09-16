import tempfile
import unittest
from pathlib import Path

from post129_pebble import can_toggle, solve
from post129_space_depth_xag import audit
from post137_joint_encoder_cosynth import apply


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

    def test_reversible_solver_can_forget_parent_before_child_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested.xag"
            path.write_text("AND 2 4\nAND 8192 8\nOUTPUT 16384\n")
            result = solve(path, max_states=5000, limit=2)
            self.assertEqual(result["status"], "SAT")
            actions = result["actions"]
            self.assertIn("UNCOMPUTE(13)", actions)
            self.assertIn("UNCOMPUTE(14)", actions)
            # Parent removal is dependency-legal even while its child remains live.
            self.assertTrue(can_toggle(0, 1 << 1, [0, 0]))

    def test_joint_cosynth_batch_uses_prebatch_rows(self):
        rows = (3, 5, 0)
        self.assertEqual(apply(rows, [(0, 1, 2)]), (3, 5, 1))

    def test_post137_score_has_requested_priority_fields(self):
        from post137_joint_encoder_cosynth import candidate_score, wanted_tables, VARS
        wanted = wanted_tables()
        batches = [[(0, 1, 6)]] + [[]] * 4
        score = candidate_score(tuple(VARS + [0, 0, 0]), tuple(VARS + [0, 0, 0]),
                                batches, batches, wanted, [0, 1])
        self.assertEqual(len(score), 5)
        self.assertEqual(score[2:], (2, 7, 2))

    def test_post137_affine_frame_materializes_exact_rows(self):
        from post137_joint_encoder_cosynth import materialize_affine_frames, VARS
        from qiskit import QuantumCircuit
        q = QuantumCircuit(9)
        result = materialize_affine_frames(q, tuple(VARS + [0, 0, 0]),
                                           [VARS[0], VARS[1], VARS[2]], list(range(9)), range(6, 9))
        self.assertTrue(result['exact'])
        self.assertEqual(q.count_ops().get('cx', 0), 3)

    def test_post137_beam_preserves_five_batch_history(self):
        from post137_joint_encoder_cosynth import beam_side, wanted_tables, storage_profile
        import random
        beam = beam_side(wanted_tables()['x'], [0, 1, 2, 3], 5, random.Random(7), width=4, options_per_state=5)
        self.assertTrue(beam)
        self.assertTrue(all(len(history) == 5 for _, history in beam))
        self.assertTrue(all(storage_profile(history)['peak'] <= 6 for _, history in beam))

    def test_post137_cegis_failure_support_uses_full_domain(self):
        from post137_joint_encoder_cosynth import VARS, failing_points, wanted_tables
        rows = tuple(VARS + [0, 0, 0])
        self.assertGreater(len(failing_points(rows, rows, wanted_tables())), 0)


if __name__ == "__main__":
    unittest.main()
