"""Tests for the routing operator itself."""

import unittest

from sovereign.engine import split


class TestSplit(unittest.TestCase):
    def test_exact_division(self):
        self.assertEqual(split(0, 8), (0,) * 8)
        self.assertEqual(split(8, 8), (1,) * 8)
        self.assertEqual(split(1000, 8), (125,) * 8)

    def test_remainder_goes_to_first_r_destinations(self):
        self.assertEqual(split(27, 8), (4, 4, 4, 3, 3, 3, 3, 3))
        self.assertEqual(split(1, 8), (1, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(split(7, 8), (1, 1, 1, 1, 1, 1, 1, 0))

    def test_conservation_exhaustive(self):
        for k in range(2, 11):
            for n in range(0, 5001):
                with self.subTest(k=k, n=n):
                    self.assertEqual(sum(split(n, k)), n)

    def test_imbalance_bounded_by_one(self):
        for k in range(2, 11):
            for n in range(0, 2001):
                shares = split(n, k)
                self.assertLessEqual(max(shares) - min(shares), 1)

    def test_components_are_quotient_or_ceiling(self):
        for k in range(2, 11):
            for n in range(0, 2001):
                quotient, remainder = divmod(n, k)
                shares = split(n, k)
                for share in shares:
                    self.assertIn(share, (quotient, quotient + 1))
                self.assertEqual(
                    sum(1 for s in shares if s == quotient + 1), remainder
                )

    def test_determinism(self):
        for n in (0, 1, 7, 8, 27, 4096, 123456789):
            self.assertEqual(split(n, 8), split(n, 8))

    def test_rejects_bad_arguments(self):
        with self.assertRaises(ValueError):
            split(-1, 8)
        with self.assertRaises(ValueError):
            split(5, 0)

    def test_translation_invariance(self):
        """split(n + k, k) is split(n, k) with every share incremented."""
        for n in (0, 3, 27, 1000):
            base = split(n, 8)
            shifted = split(n + 8, 8)
            self.assertEqual(shifted, tuple(s + 1 for s in base))


if __name__ == "__main__":
    unittest.main()
