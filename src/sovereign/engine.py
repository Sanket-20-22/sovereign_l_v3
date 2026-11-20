"""
engine.py -- the Connect / Resonate / Collapse (CRC) routing engine.

The engine implements one primitive: take a non-negative integer ``n`` held at
a lattice cell and distribute it among that cell's ``k`` axial neighbours so
that nothing is lost and nothing is created.

Routing operator
----------------
For a neighbourhood of size ``k`` and a quantity ``n``::

    n = k*q + r,    q = n // k,    0 <= r < k

    R_i(n) = q + 1   for i < r
             q       for i >= r

The source is set to ``Omega_source - n``, so the operator is a redistribution
and not a replication.

The engine never assumes that the ``k`` neighbours are distinct coordinates.
On a lattice small enough for two neighbours to coincide, the shares
accumulate in the shared cell, the conservation scope is de-duplicated, and
the invariant still holds exactly.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .lattice import Coord, LatticeMemory

__all__ = ["split", "CRCEngine", "InsufficientSource"]


class InsufficientSource(ValueError):
    """Raised when a routing request exceeds the quantity held at the source."""


def split(n: int, k: int) -> Tuple[int, ...]:
    """Split ``n`` into ``k`` shares differing by at most one unit.

    This is the largest-remainder rule. It is the single arithmetic operation
    on which the whole framework rests.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    if n < 0:
        raise ValueError("n must be non-negative")
    quotient, remainder = divmod(int(n), k)
    return tuple(
        quotient + (1 if i < remainder else 0) for i in range(k)
    )


class CRCEngine:
    """Connect / Resonate / Collapse over a :class:`LatticeMemory`.

    Parameters
    ----------
    memory:
        The lattice the engine operates on.
    scale:
        Lattice spacing of the neighbourhood, in units of one lattice step.
        ``scale=1`` gives the eight nearest axial neighbours in Z^4.
    """

    def __init__(self, memory: LatticeMemory, scale: int = 1) -> None:
        self.memory = memory
        self.dims = memory.dims
        self.neighbourhood_size = 2 * self.dims
        self.scale = 1
        self.set_scale(scale)

        self.centre: Optional[Coord] = None
        self.links: List[Coord] = []
        self.baseline: Optional[int] = None
        self.last_quotient = 0
        self.last_remainder = 0
        self.last_vector: Tuple[int, ...] = ()

    # ------------------------------------------------------------------
    # configuration
    # ------------------------------------------------------------------

    def set_scale(self, scale: int) -> None:
        """Set the neighbourhood spacing. Invalidates any CONNECT."""
        scale = int(scale)
        if scale < 1:
            raise ValueError("scale must be a positive integer")
        if scale != self.scale:
            self.scale = scale
            self.centre = None
            self.links = []
            self.baseline = None

    def axial_offsets(self) -> Tuple[Coord, ...]:
        """The ``2*dims`` unit displacements, ordered +e1, -e1, +e2, ..."""
        offsets: List[Coord] = []
        for axis in range(self.dims):
            for sign in (+1, -1):
                step = [0] * self.dims
                step[axis] = sign * self.scale
                offsets.append(tuple(step))
        return tuple(offsets)

    def neighbours(self, centre: Sequence[int]) -> List[Coord]:
        """Resolved neighbour coordinates of ``centre`` under the boundary policy."""
        centre = tuple(centre)
        return [
            self.memory.resolve(tuple(c + o for c, o in zip(centre, offset)))
            for offset in self.axial_offsets()
        ]

    # ------------------------------------------------------------------
    # CONNECT
    # ------------------------------------------------------------------

    def connect(self, centre: Sequence[int]) -> List[Coord]:
        """Bind the neighbourhood of ``centre`` and record the invariant baseline."""
        centre = self.memory.resolve(centre)
        self.centre = centre
        self.links = self.neighbours(centre)
        self.baseline = self.memory.total(self.scope())
        return self.links

    def scope(self) -> List[Coord]:
        """The conservation scope: centre plus neighbours, de-duplicated.

        De-duplication matters. On a periodic lattice small enough that
        +e and -e wrap onto the same cell, the raw neighbour list contains
        repeats; summing it would count those cells twice and manufacture a
        spurious invariant failure.
        """
        if self.centre is None:
            return []
        seen: Dict[Coord, None] = {self.centre: None}
        for link in self.links:
            seen[link] = None
        return list(seen.keys())

    def local_total(self) -> int:
        return self.memory.total(self.scope())

    # ------------------------------------------------------------------
    # RESONATE
    # ------------------------------------------------------------------

    def resonate(self, amount: Optional[int] = None) -> Tuple[int, ...]:
        """Route ``amount`` from the centre to the connected neighbours."""
        if self.centre is None:
            raise RuntimeError("RESONATE requires CONNECT first")

        if amount is None:
            amount = self.memory.read(self.centre)

        if not isinstance(amount, int) or isinstance(amount, bool):
            raise TypeError("routing amount must be an integer")
        if amount < 0:
            raise ValueError("routing amount must be non-negative")

        source = self.memory.read(self.centre)
        if amount > source:
            raise InsufficientSource(
                f"source holds {source}, requested {amount}"
            )

        vector = split(amount, self.neighbourhood_size)
        self.last_vector = vector
        self.last_quotient, self.last_remainder = divmod(
            amount, self.neighbourhood_size
        )

        # Source is drained first so that a neighbour coinciding with the
        # centre cannot corrupt the source state.
        self.memory.write(self.centre, source - amount)

        for link, share in zip(self.links, vector):
            if share:
                self.memory.add(link, share)

        return vector

    # ------------------------------------------------------------------
    # COLLAPSE
    # ------------------------------------------------------------------

    def collapse(self, expected: Optional[int] = None) -> bool:
        """Verify the conservation invariant for the connected scope."""
        if self.centre is None:
            raise RuntimeError("COLLAPSE requires CONNECT first")
        if expected is None:
            expected = self.baseline
        if expected is None:
            raise RuntimeError("no invariant baseline available")
        return self.local_total() == expected

    # ------------------------------------------------------------------
    # convenience
    # ------------------------------------------------------------------

    def route_at(
        self,
        centre: Sequence[int],
        amount: Optional[int] = None,
        verify: bool = True,
    ) -> Tuple[int, ...]:
        """CONNECT, RESONATE and optionally COLLAPSE in one call."""
        self.connect(centre)
        vector = self.resonate(amount)
        if verify and not self.collapse():
            raise AssertionError(
                f"conservation violated at {self.centre}: "
                f"expected {self.baseline}, observed {self.local_total()}"
            )
        return vector

    # ------------------------------------------------------------------
    # simultaneous update
    # ------------------------------------------------------------------

    def sweep(
        self,
        cells: Optional[Sequence[Coord]] = None,
        amount_of: Optional[Callable[[int], int]] = None,
    ) -> int:
        """Advance every cell at once and return the total carried.

        This is the parallel semantics: all cells read the *old* state and all
        writes land in a *new* state, so the order in which cells are visited
        cannot affect the result. Every cell routes ``amount_of(value)``
        (by default its entire value) to its axial neighbours.

        Because each source routes exactly what it gives up, the total is
        invariant: the sum of all outgoing shares equals the sum of all
        states before the sweep.
        """
        if cells is None:
            cells = self.memory.mapped()

        if amount_of is None:
            amount_of = lambda value: value  # noqa: E731

        incoming: Dict[Coord, int] = {}

        for cell in cells:
            value = self.memory.read(cell)
            if value <= 0:
                continue
            amount = amount_of(value)
            if amount < 0 or amount > value:
                raise ValueError(
                    f"amount_of returned {amount} for a cell holding {value}"
                )
            # the source keeps whatever it did not route, even when that is
            # everything: routing zero units must not delete the cell
            if amount < value:
                incoming[cell] = incoming.get(cell, 0) + (value - amount)
            if amount == 0:
                continue
            vector = split(amount, self.neighbourhood_size)
            for offset, share in zip(self.axial_offsets(), vector):
                if share:
                    target = self.memory.resolve(
                        tuple(c + o for c, o in zip(cell, offset))
                    )
                    incoming[target] = incoming.get(target, 0) + share

        self.memory._cells = {c: v for c, v in incoming.items() if v}
        return sum(incoming.values())

    def global_total(self) -> int:
        """Total integer state held by the whole lattice."""
        return self.memory.total()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"CRCEngine(dims={self.dims}, k={self.neighbourhood_size}, "
            f"scale={self.scale}, centre={self.centre})"
        )
