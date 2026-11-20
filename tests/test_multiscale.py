"""Tests for restriction, prolongation and the V-cycle."""

import random
import unittest
from itertools import product

from sovereign.lattice import Boundary, LatticeMemory
from sovereign.multiscale import Hierarchy


def seeded(extent=4, block=(2, 2, 2, 2), seed=11, high=200):
    memory = LatticeMemory(
        dims=4, extents=(extent,) * 4, policy=Boundary.PERIODIC
    )
    rng = random.Random(seed)
    for coord in product(range(extent), repeat=4):
        memory.write(coord, rng.randint(0, high))
    return memory, Hierarchy(memory, block=block)


class TestTopology(unittest.TestCase):
    def test_children_per_parent(self):
        memory, hierarchy = seeded()
        self.assertEqual(hierarchy.k, 16)
        self.assertEqual(len(hierarchy.children((0, 0, 0, 0))), 16)
        self.assertEqual(len(hierarchy.parents()), 16)

    def test_parent_of_is_the_inverse(self):
        memory, hierarchy = seeded()
        for child in hierarchy.children((1, 1, 1, 1)):
            self.assertEqual(hierarchy.parent_of(child), (1, 1, 1, 1))

    def test_children_partition_the_lattice(self):
        memory, hierarchy = seeded()
        seen = set()
        for parent in hierarchy.parents():
            seen.update(hierarchy.children(parent))
        self.assertEqual(len(seen), 4 ** 4)

    def test_block_of_eight_gives_eight_children(self):
        memory = LatticeMemory(
            dims=4, extents=(4, 4, 4, 4), policy=Boundary.PERIODIC
        )
        hierarchy = Hierarchy(memory, block=(2, 2, 2, 1))
        self.assertEqual(hierarchy.k, 8)


class TestRestriction(unittest.TestCase):
    def test_restriction_sums_children(self):
        memory, hierarchy = seeded()
        coarse = hierarchy.restrict()
        self.assertEqual(sum(coarse.values()), memory.total())
        for parent, value in coarse.items():
            self.assertEqual(
                value, sum(memory.read(c) for c in hierarchy.children(parent))
            )


class TestProlongation(unittest.TestCase):
    def test_prolongation_splits_exactly(self):
        memory, hierarchy = seeded()
        hierarchy.restrict()
        total = memory.total()
        hierarchy.prolong()
        self.assertEqual(memory.total(), total)

    def test_prolongation_of_a_single_value(self):
        memory, hierarchy = seeded(high=0)
        for parent in hierarchy.parents():
            hierarchy.coarse_memory.write(parent, 0)
        hierarchy.coarse_memory.write((0, 0, 0, 0), 27)
        hierarchy.prolong()
        shares = [memory.read(c) for c in hierarchy.children((0, 0, 0, 0))]
        self.assertEqual(sum(shares), 27)
        self.assertEqual(sorted(set(shares)), [1, 2])


class TestVCycle(unittest.TestCase):
    def test_single_cycle_conserves(self):
        memory, hierarchy = seeded()
        start = memory.total()
        self.assertTrue(hierarchy.vcycle())
        self.assertEqual(memory.total(), start)

    def test_repeated_cycles_conserve(self):
        memory, hierarchy = seeded(seed=12)
        start = memory.total()
        for _ in range(6):
            self.assertTrue(hierarchy.vcycle(passes=2))
        self.assertEqual(memory.total(), start)

    def test_cycle_changes_the_field(self):
        memory, hierarchy = seeded(seed=13)
        before = dict(memory.items())
        hierarchy.vcycle()
        self.assertNotEqual(before, dict(memory.items()))

    def test_cycle_without_coarse_routing_preserves_parent_sums(self):
        memory, hierarchy = seeded(seed=14)
        before = {
            parent: sum(memory.read(c) for c in hierarchy.children(parent))
            for parent in hierarchy.parents()
        }
        hierarchy.vcycle(passes=0)
        after = {
            parent: sum(memory.read(c) for c in hierarchy.children(parent))
            for parent in hierarchy.parents()
        }
        self.assertEqual(before, after)
        self.assertEqual(memory.total(), sum(before.values()))

    def test_coarse_total_tracks_fine_total(self):
        memory, hierarchy = seeded(seed=15)
        start = memory.total()
        hierarchy.vcycle(passes=3)
        self.assertEqual(hierarchy.coarse_total(), start)


class TestValidation(unittest.TestCase):
    def test_requires_bounded_lattice(self):
        with self.assertRaises(ValueError):
            Hierarchy(LatticeMemory(dims=4))

    def test_rejects_indivisible_extent(self):
        memory = LatticeMemory(
            dims=4, extents=(3, 3, 3, 3), policy=Boundary.PERIODIC
        )
        with self.assertRaises(ValueError):
            Hierarchy(memory, block=(2, 2, 2, 2))

    def test_rejects_single_child_block(self):
        memory = LatticeMemory(
            dims=4, extents=(4, 4, 4, 4), policy=Boundary.PERIODIC
        )
        with self.assertRaises(ValueError):
            Hierarchy(memory, block=(1, 1, 1, 1))


if __name__ == "__main__":
    unittest.main()
