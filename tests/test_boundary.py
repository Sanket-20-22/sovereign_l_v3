"""Boundary policy tests, including the small-lattice coincidence case."""

import unittest

from sovereign.engine import CRCEngine
from sovereign.lattice import Boundary, BoundaryError, LatticeMemory


class TestUnbounded(unittest.TestCase):
    def test_coordinates_are_used_as_given(self):
        memory = LatticeMemory(dims=4)
        memory.write((-7, 3, 0, 12), 5)
        self.assertEqual(memory.read((-7, 3, 0, 12)), 5)
        self.assertEqual(memory.read((7, 3, 0, 12)), 0)

    def test_routing_creates_cells_beyond_the_seed(self):
        memory = LatticeMemory(dims=4)
        engine = CRCEngine(memory)
        memory.write((0, 0, 0, 0), 8)
        engine.route_at((0, 0, 0, 0), 8)
        # the drained centre stays mapped, plus its eight neighbours
        self.assertEqual(memory.cell_count(), 9)
        self.assertEqual(memory.total(), 8)


class TestPeriodic(unittest.TestCase):
    def test_wrapping_read_write(self):
        memory = LatticeMemory(
            dims=4, extents=(4, 4, 4, 4), policy=Boundary.PERIODIC
        )
        memory.write((5, 0, 0, 0), 9)
        self.assertEqual(memory.read((1, 0, 0, 0)), 9)

    def test_neighbours_wrap(self):
        memory = LatticeMemory(
            dims=4, extents=(4, 4, 4, 4), policy=Boundary.PERIODIC
        )
        engine = CRCEngine(memory)
        links = engine.connect((0, 0, 0, 0))
        self.assertIn((3, 0, 0, 0), links)

    def test_conservation_holds_across_the_seam(self):
        memory = LatticeMemory(
            dims=4, extents=(4, 4, 4, 4), policy=Boundary.PERIODIC
        )
        engine = CRCEngine(memory)
        memory.write((0, 0, 0, 0), 27)
        engine.route_at((0, 0, 0, 0), 27)
        self.assertEqual(memory.total(), 27)


class TestCoincidentNeighbours(unittest.TestCase):
    """On a 2x2x2x2 torus, +e and -e land on the same cell.

    The raw neighbour list therefore contains repeats. The engine must
    accumulate the shares and de-duplicate the conservation scope, otherwise
    the invariant check reports a false failure.
    """

    def setUp(self):
        self.memory = LatticeMemory(
            dims=4, extents=(2, 2, 2, 2), policy=Boundary.PERIODIC
        )
        self.engine = CRCEngine(self.memory)

    def test_neighbour_list_has_repeats(self):
        links = self.engine.connect((0, 0, 0, 0))
        self.assertEqual(len(links), 8)
        self.assertEqual(len(set(links)), 4)

    def test_scope_is_de_duplicated(self):
        self.engine.connect((0, 0, 0, 0))
        self.assertEqual(len(self.engine.scope()), 5)

    def test_conservation_holds_despite_coincidence(self):
        self.memory.write((0, 0, 0, 0), 27)
        self.engine.connect((0, 0, 0, 0))
        self.engine.resonate(27)
        self.assertTrue(self.engine.collapse())
        self.assertEqual(self.memory.total(), 27)

    def test_shares_accumulate_in_the_shared_cell(self):
        self.memory.write((0, 0, 0, 0), 8)
        self.engine.connect((0, 0, 0, 0))
        self.engine.resonate(8)
        # each of the four distinct neighbours receives two shares of 1
        for coord in set(self.engine.links):
            self.assertEqual(self.memory.read(coord), 2)


class TestAbsorbing(unittest.TestCase):
    def test_write_outside_raises(self):
        memory = LatticeMemory(
            dims=4, extents=(3, 3, 3, 3), policy=Boundary.ABSORBING
        )
        with self.assertRaises(BoundaryError):
            memory.write((3, 0, 0, 0), 1)

    def test_read_outside_returns_zero(self):
        memory = LatticeMemory(
            dims=4, extents=(3, 3, 3, 3), policy=Boundary.ABSORBING
        )
        self.assertEqual(memory.read((-1, 0, 0, 0)), 0)

    def test_routing_at_a_face_is_refused(self):
        memory = LatticeMemory(
            dims=4, extents=(3, 3, 3, 3), policy=Boundary.ABSORBING
        )
        engine = CRCEngine(memory)
        memory.write((0, 0, 0, 0), 8)
        engine.connect((0, 0, 0, 0))
        with self.assertRaises(BoundaryError):
            engine.resonate(8)

    def test_interior_routing_is_fine(self):
        memory = LatticeMemory(
            dims=4, extents=(3, 3, 3, 3), policy=Boundary.ABSORBING
        )
        engine = CRCEngine(memory)
        memory.write((1, 1, 1, 1), 8)
        engine.route_at((1, 1, 1, 1), 8)
        self.assertEqual(memory.total(), 8)


class TestValidation(unittest.TestCase):
    def test_wrong_arity(self):
        with self.assertRaises(ValueError):
            LatticeMemory(dims=4).write((0, 0, 0), 1)

    def test_non_integer_coordinate(self):
        with self.assertRaises(TypeError):
            LatticeMemory(dims=4).write((0.5, 0, 0, 0), 1)

    def test_negative_value_rejected(self):
        with self.assertRaises(ValueError):
            LatticeMemory(dims=4).write((0, 0, 0, 0), -1)

    def test_periodic_requires_extents(self):
        with self.assertRaises(ValueError):
            LatticeMemory(dims=4, policy=Boundary.PERIODIC)

    def test_total_de_duplicates_input(self):
        memory = LatticeMemory(dims=4)
        memory.write((0, 0, 0, 0), 7)
        self.assertEqual(memory.total([(0, 0, 0, 0)] * 5), 7)


if __name__ == "__main__":
    unittest.main()
