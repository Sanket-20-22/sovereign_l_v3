"""
assembler.py -- two-pass assembler for the Sovereign-L v3 ISA.

Pass one records label addresses by accumulating declared instruction lengths.
Pass two emits bytes and resolves label references. Every operand is
range-checked against its declared width, so a value that does not fit is a
compile error rather than a truncated instruction.

Syntax
------
::

    ; comment           (# also starts a comment)
    LABEL:              label definition
        LOAD_VAL 27     mnemonic followed by whitespace-separated operands
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from .isa import (
    BY_CODE,
    COORD_RANGE,
    OPCODES,
    UNSIGNED_BYTE,
    UNSIGNED_SHORT,
    encode_s8,
    encode_u16,
)

__all__ = ["Assembler", "AssemblyError", "disassemble"]


class AssemblyError(ValueError):
    """Raised for any source-level problem, with the offending line number."""

    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


def _strip_comment(text: str) -> str:
    for marker in (";", "#"):
        if marker in text:
            text = text.split(marker, 1)[0]
    return text.strip()


class Assembler:
    """Assembles source text into a flat list of byte values."""

    def __init__(self) -> None:
        self.labels: Dict[str, int] = {}

    # ------------------------------------------------------------------

    def _parse(self, source: str) -> List[Tuple[int, str, List[str]]]:
        """Return (line number, mnemonic, operands) for every instruction."""
        parsed: List[Tuple[int, str, List[str]]] = []
        for number, raw in enumerate(source.splitlines(), start=1):
            text = _strip_comment(raw)
            if not text:
                continue

            if text.endswith(":"):
                label = text[:-1].strip().upper()
                if not label:
                    raise AssemblyError(number, "empty label")
                if label in self.labels:
                    raise AssemblyError(number, f"duplicate label {label}")
                self.labels[label] = -1  # patched in pass one
                continue

            parts = text.split()
            mnemonic = parts[0].upper()
            if mnemonic not in OPCODES:
                raise AssemblyError(number, f"unknown mnemonic {mnemonic}")
            parsed.append((number, mnemonic, parts[1:]))
        return parsed

    # ------------------------------------------------------------------

    def assemble(self, source: str) -> List[int]:
        """Assemble ``source`` and return the byte stream."""
        self.labels = {}
        parsed = self._parse(source)

        # ---- pass one: label addresses -------------------------------
        # Labels were recorded during parsing; walk again to fix addresses.
        self.labels = {}
        address = 0
        instruction_addresses: List[int] = []
        for number, raw in enumerate(source.splitlines(), start=1):
            text = _strip_comment(raw)
            if not text:
                continue
            if text.endswith(":"):
                label = text[:-1].strip().upper()
                if label in self.labels:
                    raise AssemblyError(number, f"duplicate label {label}")
                self.labels[label] = address
                continue
            mnemonic = text.split()[0].upper()
            instruction_addresses.append(address)
            address += OPCODES[mnemonic].length

        if address > UNSIGNED_SHORT[1]:
            raise AssemblyError(
                0,
                f"program is {address} bytes; the address space is "
                f"{UNSIGNED_SHORT[1] + 1} bytes",
            )

        # ---- pass two: emit ------------------------------------------
        stream: List[int] = []
        for (number, mnemonic, operands), expected_address in zip(
            parsed, instruction_addresses
        ):
            if len(stream) != expected_address:  # pragma: no cover - defensive
                raise AssemblyError(number, "internal address mismatch")
            opcode = OPCODES[mnemonic]
            if len(operands) != len(opcode.operands):
                raise AssemblyError(
                    number,
                    f"{mnemonic} expects {len(opcode.operands)} operands, "
                    f"got {len(operands)}",
                )

            stream.append(opcode.code)
            for kind, token in zip(opcode.operands, operands):
                stream.extend(self._encode_operand(number, kind, token))

        return stream

    # ------------------------------------------------------------------

    def _encode_operand(self, line: int, kind: str, token: str) -> List[int]:
        try:
            value = int(token, 0)
        except ValueError:
            if kind == "u16" and token.upper() in self.labels:
                value = self.labels[token.upper()]
                if value < 0:  # pragma: no cover - defensive
                    raise AssemblyError(line, f"label {token} has no address")
            else:
                raise AssemblyError(line, f"operand {token!r} is not an integer")

        if kind == "s8":
            low, high = COORD_RANGE
            if not (low <= value <= high):
                raise AssemblyError(
                    line, f"operand {value} outside signed byte range [{low}, {high}]"
                )
            return [encode_s8(value)]
        if kind == "u8":
            low, high = UNSIGNED_BYTE
            if not (low <= value <= high):
                raise AssemblyError(
                    line, f"operand {value} outside byte range [{low}, {high}]"
                )
            return [value & 0xFF]
        if kind == "u16":
            low, high = UNSIGNED_SHORT
            if not (low <= value <= high):
                raise AssemblyError(
                    line,
                    f"operand {value} outside 16-bit range [{low}, {high}]",
                )
            return list(encode_u16(value))
        raise AssemblyError(line, f"unknown operand kind {kind}")  # pragma: no cover


def disassemble(stream: Sequence[int]) -> List[str]:
    """Best-effort disassembly, for debugging and test output."""
    from .isa import decode_s8, decode_u16

    out: List[str] = []
    index = 0
    while index < len(stream):
        opcode = BY_CODE.get(stream[index])
        if opcode is None:
            out.append(f"{index:04d}: .byte 0x{stream[index]:02x}")
            index += 1
            continue
        cursor = index + 1
        rendered: List[str] = []
        for kind in opcode.operands:
            if kind == "u16":
                rendered.append(str(decode_u16(stream[cursor], stream[cursor + 1])))
                cursor += 2
            elif kind == "s8":
                rendered.append(str(decode_s8(stream[cursor])))
                cursor += 1
            else:
                rendered.append(str(stream[cursor]))
                cursor += 1
        out.append(
            f"{index:04d}: {opcode.name:<11} {' '.join(rendered)}".rstrip()
        )
        index = cursor
    return out
