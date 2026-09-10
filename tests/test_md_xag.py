import unittest

from md_xag import AndNode, XAG, build_balanced_anf_xag, logo_truth_table


class MDXAGTests(unittest.TestCase):
    def test_two_input_and_metrics(self):
        graph = XAG([AndNode(1 << 1, 1 << 2)], 1 << 13)
        expected = sum(
            1 << point for point in range(4096) if (point & 1) and (point & 2)
        )
        self.assertEqual(graph.evaluate(), expected)
        metrics = graph.metrics(expected)
        self.assertTrue(metrics["exact"])
        self.assertEqual(metrics["multiplicative_depth"], 1)
        self.assertEqual(metrics["and_count"], 1)

    def test_live_width_uses_last_use(self):
        graph = XAG(
            [
                AndNode(1 << 1, 1 << 2),
                AndNode(1 << 3, 1 << 4),
            ],
            1 << 14,
        )
        self.assertEqual(graph.live_width(), 1)

    def test_balanced_anf_is_exact_and_depth_four(self):
        graph = build_balanced_anf_xag()
        self.assertEqual(graph.evaluate(), logo_truth_table())
        metrics = graph.metrics()
        self.assertTrue(metrics["exact"])
        self.assertEqual(metrics["multiplicative_depth"], 4)
        self.assertEqual(metrics["and_layer_widths"], [2767, 1390, 812, 127])


if __name__ == "__main__":
    unittest.main()
