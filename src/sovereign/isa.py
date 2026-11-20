"""
isa.py -- instruction set for the Sovereign-L integer routing machine (v3).

Encoding is little-endian, variable length, byte oriented. Every operand has a
declared width and the assembler range-checks it; nothing is silently
truncated.

Changes from the earlier three-opcode sketch
--------------------------------------------
* CONNECT carries an explicit centre, so a program can route from any cell
  instead of being pinned to the origin.
* Jump targets are 16-bit, so programs are no longer capped at 256 bytes.
* Coordinates are signed bytes, so negative lattice coordinates are
  representable.
* Frame identifiers are 16-bit, so the addressable space is not capped at 256
  cells.
* SET_EXTENT declares the boundary policy, because a finite scheme without one
  leaks state.
* SWEEP performs a simultaneous update of every mapped cell.
"""

from __future__ import annotations

from typing import Dict, NamedTuple, Tuple

__all__ = [
    "Opcode",
    "OPCODES",
    "SIGNED_BYTE",
    "UNSIGNED_BYTE",
    "UNSIGNED_SHORT",
    "COORD_RANGE",
    "encode_s8",
    "decode_s8",
    "encode_u16",
    "decode_u16",
]

SIGNED_BYTE = (-128, 127)
UNSIGNED_BYTE = (0, 255)
UNSIGNED_SHORT = (0, 65535)
COORD_RANGE = SIGNED_BYTE


class Opcode(NamedTuple):
    name: str
    code: int
    operands: Tuple[str, ...]
    summary: str

    @property
    def length(self) -> int:
        """Total encoded length in bytes, including the opcode byte."""
        size = 1
        for kind in self.operands:
            size += 2 if kind == "u16" else 1
        return size


OPCODES: Dict[str, Opcode] = {
    op.name: op
    for op in (
        Opcode("NOP", 0x00, (), "do nothing"),
        Opcode("LOAD_VAL", 0x01, ("u16",), "AL <- immediate"),
        Opcode("DIV_MOD_K", 0x02, (), "AL, R <- divmod(AL, k)"),
        Opcode("ADD_REG", 0x03, ("s8",), "AL <- AL + immediate"),
        Opcode("SUB_REG", 0x04, ("s8",), "AL <- AL - immediate"),
        Opcode("MMU_MAP", 0x05, ("s8", "s8", "s8", "s8", "u16"),
               "bind coordinate to frame"),
        Opcode("STORE_CELL", 0x06, ("s8", "s8", "s8", "s8"), "cell <- AL"),
        Opcode("FETCH_CELL", 0x07, ("s8", "s8", "s8", "s8"), "AL <- cell"),
        Opcode("SET_SCALE", 0x08, ("u8",), "set neighbourhood spacing"),
        Opcode("SET_EXTENT", 0x09, ("s8", "s8", "s8", "s8"),
               "declare periodic extents (all zero = unbounded)"),
        Opcode("CONNECT", 0x0A, ("s8", "s8", "s8", "s8"),
               "bind neighbourhood of an explicit centre"),
        Opcode("RESONATE", 0x0B, (), "route AL from the centre"),
        Opcode("COLLAPSE", 0x0C, (), "verify the conservation invariant"),
        Opcode("SWEEP", 0x0D, (), "simultaneous update of every mapped cell"),
        Opcode("JMP", 0x0E, ("u16",), "unconditional jump"),
        Opcode("JMP_NZ", 0x0F, ("u16",), "jump when AL != 0"),
        Opcode("HALT", 0xFF, (), "stop the machine"),
    )
}

BY_CODE: Dict[int, Opcode] = {op.code: op for op in OPCODES.values()}


def encode_s8(value: int) -> int:
    low, high = COORD_RANGE
    if not (low <= value <= high):
        raise ValueError(f"signed byte out of range [{low}, {high}]: {value}")
    return value & 0xFF


def decode_s8(byte: int) -> int:
    return byte - 0x100 if byte >= 0x80 else byte


def encode_u16(value: int) -> Tuple[int, int]:
    low, high = UNSIGNED_SHORT
    if not (low <= value <= high):
        raise ValueError(f"unsigned short out of range [{low}, {high}]: {value}")
    return value & 0xFF, (value >> 8) & 0xFF


def decode_u16(lo: int, hi: int) -> int:
    return lo | (hi << 8)
