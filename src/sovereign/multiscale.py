"""
multiscale.py -- two-level (and recursive) restriction / prolongation over the
CRC routing operator.

A hierarchy groups ``k`` fine cells under one coarse cell. Two operators move
state between the levels:

    restriction   parent value = sum of its children
    prolongation  child values = split(parent value, k)

Both are exact on integers, so a cycle that restricts, routes at the coarse
level and prolongs returns the fine lattice to exactly the same total. That is
the whole point: a multilevel scheme is *not* where the invariant gets lost,
provided both transfer operators are conservative.

The coarse level is routed with the same :class:`~sovereign.engine.CRCEngine`
used at the fine level, with a periodic boundary on the coarse extents. A
boundary policy is mandatory here -- without one, routing at the coarse level
writes to coordinates that no level owns and the state silently leaks away.
"""

from __future__ import annotations

import itertools
from typing import Dict, List, Optional, Sequence, Tuple

from .engine import CRCEngine, split
from .lattice import Boundary, Coord, LatticeMemory

__all__ = ["Hierarchy"]


class Hierarchy:
    """Restriction / prolongation / V-cycle over a bounded fine lattice.

    Parameters
    ----------
    memory:
        Fine lattice. Must be bounded (``extents`` set).
    block:
        Children per parent along each axis. The number of children per parent
        is the product of ``block`` and must be >= 2.
    """

    def __init__(
        self,
        memory: LatticeMemory,
        block: Optional[Sequence[int]] = None,
    ) -> None:
        if memory.extents is None:
            raise ValueError("a hierarchy requires a bounded fine lattice")
        self.memory = memory
        self.dims = memory.dims
        self.block = tuple(int(b) for b in (block or (2,) * self.dims))
        if len(self.block) != self.dims:
            raise ValueError("block must have one entry per dimension")
        if any(b < 1 for b in self.block):
            raise ValueError("block entries must be >= 1")
        for extent, factor in zip(memory.extents, self.block):
            if extent % factor:
                raise ValueError(
                    f"extent {extent} is not divisible by block {factor}"
                )
        self.k = 1
        for b in self.block:
            self.k *= b
        if self.k < 2:
            raise ValueError("a parent must own at least two children")

        self.coarse_extents = tuple(
            e // b for e, b in zip(memory.extents, self.block)
        )
        self.coarse_memory = LatticeMemory(
            self.dims, self.coarse_extents, Boundary.PERIODIC
        )
        self.coarse_engine = CRCEngine(self.coarse_memory)

    # ------------------------------------------------------------------
    # topology
    # ------------------------------------------------------------------

    def parents(self) -> List[Coord]:
        return [
            tuple(idx)
            for idx in itertools.product(
                *(range(e) for e in self.coarse_extents)
            )
        ]

    def children(self, parent: Sequence[int]) -> List[Coord]:
        """The fine coordinates owned by ``parent``, in a fixed order."""
        ranges = [
            range(p * b, (p + 1) * b)
            for p, b in zip(parent, self.block)
        ]
        return [tuple(c) for c in itertools.product(*ranges)]

    def parent_of(self, coord: Sequence[int]) -> Coord:
        return tuple(c // b for c, b in zip(coord, self.block))

    # ------------------------------------------------------------------
    # transfer operators
    # ------------------------------------------------------------------

    def restrict(self) -> Dict[Coord, int]:
        """Fine -> coarse. Each parent receives the exact sum of its children."""
        coarse: Dict[Coord, int] = {}
        for parent in self.parents():
            coarse[parent] = sum(
                self.memory.read(child) for child in self.children(parent)
            )
        for parent, value in coarse.items():
            self.coarse_memory.write(parent, value)
        return coarse

    def prolong(self) -> None:
        """Coarse -> fine. Each parent's value is split among its children."""
        for parent in self.parents():
            value = self.coarse_memory.read(parent)
            shares = split(value, self.k)
            for child, share in zip(self.children(parent), shares):
                self.memory.write(child, share)

    # ------------------------------------------------------------------
    # cycle
    # ------------------------------------------------------------------

    def vcycle(self, passes: int = 1, verify: bool = True) -> bool:
        """One restrict -> coarse route -> prolong cycle.

        Returns True when the fine total is unchanged. Raises
        ``AssertionError`` instead when ``verify`` is set and the total moved,
        because a silent loss of state is the failure mode this module exists
        to rule out.
        """
        if passes < 0:
            raise ValueError("passes must be >= 0")

        before = self.memory.total()
        self.restrict()

        for _ in range(passes):
            self.coarse_engine.sweep(self.parents())

        self.prolong()
        after = self.memory.total()

        if verify and after != before:
            raise AssertionError(
                f"V-cycle lost state: {before} -> {after}"
            )
        return after == before

    def coarse_total(self) -> int:
        return self.coarse_memory.total()

    def fine_total(self) -> int:
        return self.memory.total()
