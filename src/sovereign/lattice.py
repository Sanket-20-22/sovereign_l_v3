"""
lattice.py -- integer state memory for a finite or unbounded d-dimensional
integer lattice.

The lattice is a sparse map from coordinate tuple to non-negative integer.
All coordinate resolution (periodic wrapping, absorbing boundaries) is done
here so that the routing engine never has to know which boundary policy is in
force.

Boundary policies
-----------------
UNBOUNDED  coordinates are used exactly as given (Z^d). Nothing is bounded.
PERIODIC   coordinates wrap modulo ``extents``. Requires ``extents``.
ABSORBING  coordinates outside ``extents`` are not part of the lattice.
           Writing outside raises ``BoundaryError``; reading outside returns 0.

The choice of policy is a modelling decision, not an implementation detail: a
routing step on a finite lattice is only defined once the policy is fixed.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

Coord = Tuple[int, ...]


class Boundary(Enum):
    """Boundary policy for a lattice."""

    UNBOUNDED = "unbounded"
    PERIODIC = "periodic"
    ABSORBING = "absorbing"


class BoundaryError(ValueError):
    """Raised when a coordinate is written outside an absorbing lattice."""


class LatticeMemory:
    """Sparse integer state over a d-dimensional lattice.

    Parameters
    ----------
    dims:
        Number of lattice dimensions. ``dims=4`` gives Z^4.
    extents:
        Per-dimension size, required for PERIODIC and ABSORBING.
    policy:
        One of the :class:`Boundary` members.
    """

    __slots__ = ("dims", "extents", "policy", "_cells")

    def __init__(
        self,
        dims: int = 4,
        extents: Optional[Sequence[int]] = None,
        policy: Boundary = Boundary.UNBOUNDED,
    ) -> None:
        if dims < 1:
            raise ValueError("dims must be >= 1")
        self.dims = int(dims)
        self.policy = policy

        if extents is None:
            if policy is not Boundary.UNBOUNDED:
                raise ValueError(
                    f"policy {policy.value} requires extents"
                )
            self.extents = None
        else:
            extents = tuple(int(e) for e in extents)
            if len(extents) != self.dims:
                raise ValueError(
                    f"extents must have {self.dims} entries, got {len(extents)}"
                )
            if any(e < 1 for e in extents):
                raise ValueError("every extent must be >= 1")
            self.extents = extents

        self._cells: Dict[Coord, int] = {}

    # ------------------------------------------------------------------
    # coordinate handling
    # ------------------------------------------------------------------

    def _check_coord(self, coord: Sequence[int]) -> Coord:
        coord = tuple(coord)
        if len(coord) != self.dims:
            raise ValueError(
                f"coordinate must have {self.dims} entries, got {len(coord)}"
            )
        for value in coord:
            if not isinstance(value, int):
                raise TypeError("coordinate entries must be integers")
        return coord

    def in_bounds(self, coord: Sequence[int]) -> bool:
        """True if ``coord`` lies inside an absorbing lattice."""
        coord = self._check_coord(coord)
        if self.extents is None:
            return True
        return all(0 <= c < e for c, e in zip(coord, self.extents))

    def resolve(self, coord: Sequence[int]) -> Coord:
        """Apply the boundary policy to a coordinate.

        PERIODIC wraps. UNBOUNDED returns the coordinate unchanged. ABSORBING
        returns the coordinate unchanged and lets callers detect out-of-range
        coordinates with :meth:`in_bounds`.
        """
        coord = self._check_coord(coord)
        if self.policy is Boundary.PERIODIC:
            return tuple(c % e for c, e in zip(coord, self.extents))
        return coord

    # ------------------------------------------------------------------
    # cell access
    # ------------------------------------------------------------------

    def read(self, coord: Sequence[int]) -> int:
        """Read a cell. Unmapped cells read as 0."""
        coord = self._check_coord(coord)
        if self.policy is Boundary.ABSORBING and not self.in_bounds(coord):
            return 0
        return self._cells.get(self.resolve(coord), 0)

    def write(self, coord: Sequence[int], value: int) -> None:
        """Write a cell. Values must be integers and non-negative."""
        coord = self._check_coord(coord)
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("cell value must be an integer")
        if value < 0:
            raise ValueError(f"cell value must be non-negative, got {value}")
        if self.policy is Boundary.ABSORBING and not self.in_bounds(coord):
            raise BoundaryError(
                f"coordinate {coord} is outside absorbing lattice {self.extents}"
            )
        self._cells[self.resolve(coord)] = int(value)

    def add(self, coord: Sequence[int], delta: int) -> None:
        """Add ``delta`` to a cell, respecting the boundary policy."""
        self.write(coord, self.read(coord) + delta)

    # ------------------------------------------------------------------
    # aggregate queries
    # ------------------------------------------------------------------

    def total(self, coords: Optional[Iterable[Sequence[int]]] = None) -> int:
        """Sum a collection of coordinates, or the whole lattice if omitted.

        Coordinates are de-duplicated, so a repeated coordinate is never
        counted twice. This is what keeps the conservation check honest on a
        lattice small enough for neighbours to coincide.
        """
        if coords is None:
            return sum(self._cells.values())
        seen = set()
        total = 0
        for coord in coords:
            key = self.resolve(coord)
            if key in seen:
                continue
            seen.add(key)
            total += self._cells.get(key, 0)
        return total

    def distinct_total(self, coords: Iterable[Sequence[int]]) -> int:
        """Alias of :meth:`total` kept for readability at call sites."""
        return self.total(coords)

    def mapped(self) -> List[Coord]:
        """All coordinates that have been written."""
        return list(self._cells.keys())

    def cell_count(self) -> int:
        return len(self._cells)

    def copy(self) -> "LatticeMemory":
        clone = LatticeMemory(self.dims, self.extents, self.policy)
        clone._cells = dict(self._cells)
        return clone

    def items(self) -> Iterator[Tuple[Coord, int]]:
        return iter(self._cells.items())

    def __len__(self) -> int:
        return len(self._cells)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"LatticeMemory(dims={self.dims}, extents={self.extents}, "
            f"policy={self.policy.value}, cells={len(self._cells)})"
        )
