"""Tests for the CRC engine: CONNECT, RESONATE, COLLAPSE."""

import unittest

from sovereign.engine import CRCEngine, InsufficientSource
from sovereign.lattice import LatticeMemory


def fresh(dims=4):
    memory = LatticeMemory(dims=dims)
    return memory, CRCEngine(memory)


class TestConnect(unittest.TestCase):
    def test_eight_axial_neighbours_in_z4(self):
        memory, engine = fresh()
        links = engine.connect((0, 0, 0, 0))
        self.assertEqual(len(links), 8)
        self.assertEqual(len(set(links)), 8)
        for link in links:
            distance = sum(abs(c) for c in link)
            self.assertEqual(distance, 1)

    def test_scale_changes_spacing(self):
        memory, engine = fresh()
        engine.set_scale(3)
        links = engine.connect((1, 1, 1, 1))
        for link in links:
            self.assertEqual(sum(abs(a - b) for a, b in zip(link, (1, 1, 1, 1))), 3)

    def test_scale_change_invalidates_connect(self):
        memory, engine = fresh()
        engine.connect((0, 0, 0, 0))
        engine.set_scale(2)
        self.assertIsNone(engine.centre)
        self.assertEqual(engine.links, [])

    def test_baseline_is_scope_total(self):
        memory, engine = fresh()
        memory.write((0, 0, 0, 0), 10)
        memory.write((1, 0, 0, 0), 5)
        engine.connect((0, 0, 0, 0))
        self.assertEqual(engine.baseline, 15)


class TestResonate(unittest.TestCase):
    def test_routing_vector_matches_split(self):
        memory, engine = fresh()
        memory.write((0, 0, 0, 0), 27)
        engine.connect((0, 0, 0, 0))
        self.assertEqual(engine.resonate(27), (4, 4, 4, 3, 3, 3, 3, 3))

    def test_source_is_drained(self):
        memory, engine = fresh()
        memory.write((0, 0, 0, 0), 100)
        engine.connect((0, 0, 0, 0))
        engine.resonate(60)
        self.assertEqual(memory.read((0, 0, 0, 0)), 40)

    def test_partial_routing_keeps_the_rest(self):
        memory, engine = fresh()
        memory.write((0, 0, 0, 0), 10)
        engine.connect((0, 0, 0, 0))
        engine.resonate(3)
        self.assertEqual(memory.read((0, 0, 0, 0)), 7)

    def test_default_amount_is_the_whole_cell(self):
        memory, engine = fresh()
        memory.write((0, 0, 0, 0), 17)
        engine.connect((0, 0, 0, 0))
        engine.resonate()
        self.assertEqual(memory.read((0, 0, 0, 0)), 0)

    def test_insufficient_source_is_refused_without_mutation(self):
        memory, engine = fresh()
        memory.write((0, 0, 0, 0), 5)
        engine.connect((0, 0, 0, 0))
        before = memory.total(engine.scope())
        with self.assertRaises(InsufficientSource):
            engine.resonate(6)
        self.assertEqual(memory.read((0, 0, 0, 0)), 5)
        self.assertEqual(memory.total(engine.scope()), before)

    def test_rejects_non_integer_and_negative(self):
        memory, engine = fresh()
        memory.write((0, 0, 0, 0), 10)
        engine.connect((0, 0, 0, 0))
        with self.assertRaises(TypeError):
            engine.resonate(2.5)
        with self.assertRaises(ValueError):
            engine.resonate(-1)

    def test_resonate_requires_connect(self):
        memory, engine = fresh()
        with self.assertRaises(RuntimeError):
            engine.resonate(1)


class TestCollapse(unittest.TestCase):
    def test_passes_after_routing(self):
        memory, engine = fresh()
        memory.write((0, 0, 0, 0), 27)
        engine.connect((0, 0, 0, 0))
        engine.resonate(27)
        self.assertTrue(engine.collapse())

    def test_detects_injected_units(self):
        memory, engine = fresh()
        memory.write((0, 0, 0, 0), 27)
        engine.connect((0, 0, 0, 0))
        engine.resonate(27)
        memory.add((1, 0, 0, 0), 5)
        self.assertFalse(engine.collapse())

    def test_detects_removed_units(self):
        memory, engine = fresh()
        memory.write((0, 0, 0, 0), 27)
        engine.connect((0, 0, 0, 0))
        engine.resonate(27)
        memory.write((1, 0, 0, 0), 0)
        self.assertFalse(engine.collapse())

    def test_explicit_expected_value(self):
        memory, engine = fresh()
        memory.write((0, 0, 0, 0), 4)
        engine.connect((0, 0, 0, 0))
        self.assertTrue(engine.collapse(4))
        self.assertFalse(engine.collapse(5))


class TestRouteAt(unittest.TestCase):
    def test_route_at_conserves(self):
        for value in (0, 1, 7, 8, 27, 32, 1000, 10**6):
            memory, engine = fresh()
            memory.write((2, 2, 2, 2), value)
            engine.route_at((2, 2, 2, 2), value)
            self.assertEqual(memory.total(), value)


if __name__ == "__main__":
    unittest.main()
