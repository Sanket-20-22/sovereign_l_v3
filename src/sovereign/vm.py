"""
vm.py -- the Sovereign-L integer routing machine.

A small fetch-decode-execute loop over a byte stream with a single working
register (``AL``), a remainder register (``R``), an MMU and a CRC engine.

The machine is integer-only. There is no floating-point path, so there is no
rounding behaviour to specify.

COLLAPSE is a trapping instruction: when the conservation invariant fails, the
machine stops and records the violation. That is the architectural point of
the design -- the invariant is checked in the instruction stream rather than in
the test harness.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .engine import CRCEngine, InsufficientSource
from .isa import BY_CODE, decode_s8, decode_u16
from .lattice import Boundary
from .mmu import MMU

__all__ = ["Machine", "RuntimeFault"]


class RuntimeFault(RuntimeError):
    """Raised when the machine stops because of an instruction-level fault."""


class Machine:
    """A Sovereign-L v3 machine instance."""

    def __init__(self, dims: int = 4, trace: bool = False) -> None:
        self.dims = dims
        self.mmu = MMU(dims=dims)
        self.engine = CRCEngine(self.mmu)
        self.registers = {"AL": 0, "R": 0}
        self.pc = 0
        self.halted = False
        self.fault: Optional[str] = None
        self.violation = False
        self.trace = trace
        self.history: List[str] = []
        self.steps = 0
        self.max_steps = 1_000_000

    # ------------------------------------------------------------------
    # execution
    # ------------------------------------------------------------------

    def run(self, stream: Sequence[int]) -> "Machine":
        """Execute ``stream`` from address 0 until HALT or a fault."""
        self.pc = 0
        self.halted = False
        self.fault = None
        self.violation = False
        self.steps = 0
        program = list(stream)

        while not self.halted:
            if self.pc < 0 or self.pc >= len(program):
                self._fault(f"program counter {self.pc} outside program")
                break
            if self.steps > self.max_steps:
                self._fault("step limit exceeded")
                break
            self.steps += 1

            code = program[self.pc]
            opcode = BY_CODE.get(code)
            if opcode is None:
                self._fault(f"invalid opcode 0x{code:02x} at {self.pc}")
                break

            if self.trace:
                self.history.append(f"{self.pc:04d} {opcode.name}")

            self.pc = self._execute(opcode.name, program)

        return self

    def _execute(self, name: str, program: List[int]) -> int:
        pc = self.pc

        if name == "NOP":
            return pc + 1

        if name == "LOAD_VAL":
            self.registers["AL"] = decode_u16(program[pc + 1], program[pc + 2])
            return pc + 3

        if name == "DIV_MOD_K":
            quotient, remainder = divmod(
                self.registers["AL"], self.engine.neighbourhood_size
            )
            self.registers["AL"] = quotient
            self.registers["R"] = remainder
            return pc + 1

        if name == "ADD_REG":
            self.registers["AL"] += decode_s8(program[pc + 1])
            return pc + 2

        if name == "SUB_REG":
            self.registers["AL"] -= decode_s8(program[pc + 1])
            return pc + 2

        if name == "MMU_MAP":
            coord = self._coord(program, pc)
            frame = decode_u16(program[pc + 5], program[pc + 6])
            try:
                self.mmu.map(coord, frame)
            except Exception as error:  # AliasingError and friends
                self._fault(f"MMU_MAP failed: {error}")
            return pc + 7

        if name == "STORE_CELL":
            coord = self._coord(program, pc)
            try:
                self.mmu.write(coord, self.registers["AL"])
            except Exception as error:
                self._fault(f"STORE_CELL failed: {error}")
            return pc + 5

        if name == "FETCH_CELL":
            coord = self._coord(program, pc)
            self.registers["AL"] = self.mmu.read(coord)
            return pc + 5

        if name == "SET_SCALE":
            try:
                self.engine.set_scale(program[pc + 1])
            except Exception as error:
                self._fault(f"SET_SCALE failed: {error}")
            return pc + 2

        if name == "SET_EXTENT":
            coord = self._coord(program, pc)
            if all(value == 0 for value in coord):
                self.mmu = MMU(dims=self.dims)
                self.engine = CRCEngine(self.mmu, scale=self.engine.scale)
            else:
                if any(value < 1 for value in coord):
                    self._fault("SET_EXTENT requires all-positive extents")
                else:
                    self.mmu = MMU(dims=self.dims)
                    self.mmu.extents = coord
                    self.mmu.policy = Boundary.PERIODIC
                    self.engine = CRCEngine(self.mmu, scale=self.engine.scale)
            return pc + 5

        if name == "CONNECT":
            coord = self._coord(program, pc)
            try:
                self.engine.connect(coord)
            except Exception as error:
                self._fault(f"CONNECT failed: {error}")
            return pc + 5

        if name == "RESONATE":
            try:
                self.engine.resonate(self.registers["AL"])
            except InsufficientSource as error:
                self._fault(f"RESONATE refused: {error}")
            except Exception as error:
                self._fault(f"RESONATE failed: {error}")
            return pc + 1

        if name == "COLLAPSE":
            if not self.engine.collapse():
                self.violation = True
                self._fault(
                    "conservation violated: expected "
                    f"{self.engine.baseline}, observed {self.engine.local_total()}"
                )
            return pc + 1

        if name == "SWEEP":
            try:
                self.engine.sweep()
                if self.engine.centre is not None:
                    self.engine.connect(self.engine.centre)
            except Exception as error:
                self._fault(f"SWEEP failed: {error}")
            return pc + 1

        if name == "JMP":
            return decode_u16(program[pc + 1], program[pc + 2])

        if name == "JMP_NZ":
            if self.registers["AL"] != 0:
                return decode_u16(program[pc + 1], program[pc + 2])
            return pc + 3

        if name == "HALT":
            self.halted = True
            return pc + 1

        self._fault(f"unimplemented opcode {name}")  # pragma: no cover
        return pc + 1

    # ------------------------------------------------------------------

    @staticmethod
    def _coord(program: Sequence[int], pc: int) -> Tuple[int, int, int, int]:
        return (
            decode_s8(program[pc + 1]),
            decode_s8(program[pc + 2]),
            decode_s8(program[pc + 3]),
            decode_s8(program[pc + 4]),
        )

    def _fault(self, message: str) -> None:
        self.fault = message
        self.halted = True

    def raise_on_fault(self) -> "Machine":
        """Turn a recorded fault into an exception, for test code."""
        if self.fault:
            raise RuntimeFault(self.fault)
        return self

    @property
    def ok(self) -> bool:
        return self.fault is None and not self.violation

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Machine(pc={self.pc}, halted={self.halted}, "
            f"fault={self.fault!r}, cells={self.mmu.cell_count()})"
        )
