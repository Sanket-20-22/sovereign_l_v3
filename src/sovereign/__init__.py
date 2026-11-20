"""
Sovereign-L: exact integer routing on a discrete lattice.

A small, self-contained reference implementation of a deterministic
conservative routing operator, its multilevel extension, and an assembler plus
virtual machine that executes it.

    >>> from sovereign import LatticeMemory, CRCEngine
    >>> memory = LatticeMemory(dims=4)
    >>> engine = CRCEngine(memory)
    >>> memory.write((0, 0, 0, 0), 27)
    >>> engine.connect((0, 0, 0, 0))
    >>> engine.resonate(27)
    (4, 4, 4, 3, 3, 3, 3, 3)
    >>> engine.collapse()
    True

The package is a software reference model. It is not a hardware description
and makes no performance claim.
"""

from .assembler import Assembler, AssemblyError, disassemble
from .engine import CRCEngine, InsufficientSource, split
from .isa import OPCODES, Opcode
from .lattice import Boundary, BoundaryError, Coord, LatticeMemory
from .mmu import MMU, AliasingError
from .multiscale import Hierarchy
from .vm import Machine, RuntimeFault

__version__ = "3.0.0"

__all__ = [
    "Assembler",
    "AssemblyError",
    "AliasingError",
    "Boundary",
    "BoundaryError",
    "CRCEngine",
    "Coord",
    "Hierarchy",
    "InsufficientSource",
    "LatticeMemory",
    "MMU",
    "Machine",
    "OPCODES",
    "Opcode",
    "RuntimeFault",
    "disassemble",
    "split",
    "__version__",
]
