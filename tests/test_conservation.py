"""Conservation tests over full lattices, under both update orders."""

import random
import unittest

from sovereign.engine import CRCEngine
from sovereign.lattice import Boundary, LatticeMemory


def periodic_lattice(extent, dims=4, seed=None, high=200):
    memory = LatticeMemory(
        dims=dims, extents=(extent,) * dims, policy=Boundary.PERIODIC
    )
    rng = random.Random(seed)
    for coord in cells(extent, dims):
        memory.write(coord, rng.randint(0, high))
    return memory


def cells(extent, dims=4):
    from itertools import product

    return [tuple(c) for c in product(range(extent), repeat=dims)]


class TestRandomisedRouting(unittest.TestCase):
    def test_five_thousand_random_routes(self):
        memory = LatticeMemory(dims=4)
        engine = CRCEngine(memory)
        rng = random.Random(20261120)
        for _ in range(5000):
            amount = rng.randint(0, 10**6)
            memory.write((0, 0, 0, 0), amount)
            engine.connect((0, 0, 0, 0))
            before = memory.total()
            engine.resonate(amount)
            self.assertTrue(engine.collapse())
            self.assertEqual(memory.total(), before)


class TestSequentialSweep(unittest.TestCase):
    def test_256_cell_torus_holds_across_five_sweeps(self):
        memory = periodic_lattice(4, seed=1)
        engine = CRCEngine(memory)
        start = memory.total()
        for _ in range(5):
            for coord in cells(4):
                engine.route_at(coord)
            self.assertEqual(memory.total(), start)

    def test_4096_cell_torus_holds(self):
        memory = periodic_lattice(8, seed=2, high=500)
        engine = CRCEngine(memory)
        start = memory.total()
        for coord in cells(8):
            engine.route_at(coord)
        self.assertEqual(memory.total(), start)
        self.assertEqual(memory.cell_count(), 8 ** 4)

    def test_two_dimensional_lattice_uses_four_neighbours(self):
        memory = LatticeMemory(
            dims=2, extents=(6, 6), policy=Boundary.PERIODIC
        )
        engine = CRCEngine(memory)
        self.assertEqual(engine.neighbourhood_size, 4)
        memory.write((0, 0), 10)
        engine.route_at((0, 0), 10)
        self.assertEqual(memory.total(), 10)


class TestSimultaneousSweep(unittest.TestCase):
    def test_sweep_conserves(self):
        memory = periodic_lattice(4, seed=3)
        engine = CRCEngine(memory)
        start = memory.total()
        for _ in range(5):
            carried = engine.sweep()
            self.assertEqual(carried, start)
            self.assertEqual(memory.total(), start)

    def test_sweep_is_order_independent(self):
        memory = periodic_lattice(4, seed=4)
        engine = CRCEngine(memory)
        forward = engine.sweep(cells(4))
        after_forward = dict(memory.items())

        memory = periodic_lattice(4, seed=4)
        engine = CRCEngine(memory)
        engine.sweep(list(reversed(cells(4))))
        after_reverse = dict(memory.items())

        self.assertEqual(forward, engine.global_total())
        self.assertEqual(after_forward, after_reverse)

    def test_partial_sweep_keeps_the_unrouted_rest(self):
        memory = periodic_lattice(3, seed=5)
        engine = CRCEngine(memory)
        start = memory.total()
        engine.sweep(cells(3), amount_of=lambda value: value // 2)
        self.assertEqual(memory.total(), start)

    def test_sweep_rejects_bad_amount_function(self):
        memory = periodic_lattice(3, seed=6)
        engine = CRCEngine(memory)
        with self.assertRaises(ValueError):
            engine.sweep(cells(3), amount_of=lambda value: value + 1)


class TestScaleInvariance(unittest.TestCase):
    def test_conservation_at_three_scales(self):
        for scale in (1, 2, 3):
            with self.subTest(scale=scale):
                memory = periodic_lattice(8, seed=7, high=100)
                engine = CRCEngine(memory, scale=scale)
                start = memory.total()
                for coord in cells(8):
                    engine.route_at(coord)
                self.assertEqual(memory.total(), start)


if __name__ == "__main__":
    unittest.main()
