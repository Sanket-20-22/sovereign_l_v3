"""Tests for the assembler and the machine."""

import unittest

from sovereign.assembler import Assembler, AssemblyError, disassemble
from sovereign.isa import OPCODES
from sovereign.vm import Machine


ROUTING_PROGRAM = """
MMU_MAP 0 0 0 0 0
LOAD_VAL 27
STORE_CELL 0 0 0 0
CONNECT 0 0 0 0
RESONATE
COLLAPSE
HALT
"""


class TestAssembler(unittest.TestCase):
    def setUp(self):
        self.assembler = Assembler()

    def test_instruction_lengths_match_the_table(self):
        stream = self.assembler.assemble(ROUTING_PROGRAM)
        expected = sum(
            OPCODES[name].length
            for name in (
                "MMU_MAP", "LOAD_VAL", "STORE_CELL", "CONNECT",
                "RESONATE", "COLLAPSE", "HALT",
            )
        )
        self.assertEqual(len(stream), expected)

    def test_labels_resolve(self):
        stream = self.assembler.assemble("LOOP:\nNOP\nJMP LOOP\nHALT\n")
        self.assertEqual(stream, [0x00, 0x0E, 0x00, 0x00, 0xFF])

    def test_forward_jump_beyond_byte_range(self):
        source = "NOP\n" * 300 + "JMP END\nHALT\nEND:\nHALT\n"
        stream = self.assembler.assemble(source)
        self.assertGreater(len(stream), 255)
        # JMP at address 300, target is the first HALT after it
        self.assertEqual(stream[300], 0x0E)
        target = stream[301] | (stream[302] << 8)
        self.assertEqual(target, 304)

    def test_negative_coordinates_are_encodable(self):
        stream = self.assembler.assemble("STORE_CELL -1 0 0 0\nHALT\n")
        self.assertEqual(stream, [0x06, 0xFF, 0x00, 0x00, 0x00, 0xFF])

    def test_coordinate_out_of_range(self):
        with self.assertRaises(AssemblyError):
            self.assembler.assemble("STORE_CELL 200 0 0 0\n")

    def test_frame_out_of_range(self):
        with self.assertRaises(AssemblyError):
            self.assembler.assemble("MMU_MAP 0 0 0 0 70000\n")

    def test_unknown_mnemonic(self):
        with self.assertRaises(AssemblyError):
            self.assembler.assemble("FROBNICATE\n")

    def test_wrong_operand_count(self):
        with self.assertRaises(AssemblyError):
            self.assembler.assemble("CONNECT 0 0 0\n")

    def test_duplicate_label(self):
        with self.assertRaises(AssemblyError):
            self.assembler.assemble("A:\nNOP\nA:\nNOP\n")

    def test_undefined_label(self):
        with self.assertRaises(AssemblyError):
            self.assembler.assemble("JMP NOWHERE\n")

    def test_comments_are_ignored(self):
        source = "; a comment\nNOP # trailing\nHALT\n"
        self.assertEqual(self.assembler.assemble(source), [0x00, 0xFF])

    def test_disassembly_round_trip(self):
        stream = self.assembler.assemble(ROUTING_PROGRAM)
        text = disassemble(stream)
        self.assertTrue(any("MMU_MAP" in line for line in text))
        self.assertTrue(any("CONNECT" in line for line in text))


class TestMachine(unittest.TestCase):
    def assemble(self, source):
        return Assembler().assemble(source)

    def test_routing_program_runs(self):
        machine = Machine().run(self.assemble(ROUTING_PROGRAM))
        self.assertTrue(machine.ok, machine.fault)
        self.assertEqual(machine.mmu.read((0, 0, 0, 0)), 0)
        self.assertEqual(machine.mmu.total(), 27)

    def test_collapse_traps_on_corruption(self):
        source = ROUTING_PROGRAM.replace(
            "HALT", "LOAD_VAL 5\nSTORE_CELL 1 0 0 0\nCOLLAPSE\nHALT"
        )
        machine = Machine().run(self.assemble(source))
        self.assertTrue(machine.violation)
        self.assertIsNotNone(machine.fault)
        self.assertFalse(machine.ok)

    def test_explicit_centre_is_honoured(self):
        source = """
        LOAD_VAL 16
        STORE_CELL 3 3 3 3
        CONNECT 3 3 3 3
        RESONATE
        COLLAPSE
        HALT
        """
        machine = Machine().run(self.assemble(source))
        self.assertTrue(machine.ok, machine.fault)
        self.assertEqual(machine.engine.centre, (3, 3, 3, 3))
        self.assertEqual(machine.mmu.read((3, 3, 3, 3)), 0)
        self.assertEqual(machine.mmu.total(), 16)

    def test_negative_coordinate_at_runtime(self):
        source = """
        LOAD_VAL 8
        STORE_CELL -2 0 0 0
        CONNECT -2 0 0 0
        RESONATE
        COLLAPSE
        HALT
        """
        machine = Machine().run(self.assemble(source))
        self.assertTrue(machine.ok, machine.fault)
        self.assertEqual(machine.mmu.read((-2, 0, 0, 0)), 0)

    def test_counted_loop(self):
        source = """
        LOAD_VAL 5
        LOOP:
            SUB_REG 1
            JMP_NZ LOOP
        HALT
        """
        machine = Machine().run(self.assemble(source))
        self.assertTrue(machine.ok, machine.fault)
        self.assertEqual(machine.registers["AL"], 0)
        self.assertEqual(machine.steps, 1 + 5 * 2 + 1)

    def test_mmu_aliasing_is_rejected(self):
        source = """
        MMU_MAP 0 0 0 0 7
        MMU_MAP 1 0 0 0 7
        HALT
        """
        machine = Machine().run(self.assemble(source))
        self.assertIn("MMU_MAP failed", machine.fault or "")

    def test_set_extent_makes_a_periodic_lattice(self):
        source = """
        SET_EXTENT 4 4 4 4
        LOAD_VAL 24
        STORE_CELL 0 0 0 0
        CONNECT 0 0 0 0
        RESONATE
        COLLAPSE
        HALT
        """
        machine = Machine().run(self.assemble(source))
        self.assertTrue(machine.ok, machine.fault)
        self.assertEqual(machine.mmu.total(), 24)
        self.assertEqual(machine.mmu.read((3, 0, 0, 0)) > 0, True)

    def test_sweep_opcode(self):
        source = """
        SET_EXTENT 4 4 4 4
        LOAD_VAL 32
        STORE_CELL 0 0 0 0
        STORE_CELL 1 0 0 0
        CONNECT 0 0 0 0
        SWEEP
        COLLAPSE
        HALT
        """
        machine = Machine().run(self.assemble(source))
        self.assertTrue(machine.ok, machine.fault)
        self.assertEqual(machine.mmu.total(), 64)

    def test_step_limit_stops_an_infinite_loop(self):
        machine = Machine()
        machine.max_steps = 100
        machine.run(self.assemble("LOOP:\nJMP LOOP\n"))
        self.assertIn("step limit", machine.fault or "")

    def test_insufficient_source_is_a_fault(self):
        source = """
        LOAD_VAL 5
        STORE_CELL 0 0 0 0
        CONNECT 0 0 0 0
        LOAD_VAL 9
        RESONATE
        HALT
        """
        machine = Machine().run(self.assemble(source))
        self.assertIn("RESONATE refused", machine.fault or "")


if __name__ == "__main__":
    unittest.main()
