"""
mmu.py -- coordinate-to-frame address translation.

The MMU gives the lattice a page directory: a 4D coordinate is bound to a
frame identifier, and the frame identifier is what the ISA can address.

One invariant is enforced that the earlier prototype did not have: **a frame
may belong to exactly one coordinate, and a coordinate may own exactly one
frame.** Aliasing is rejected rather than silently allowed, because two
coordinates sharing a frame makes the same cell appear twice in a conservation
sum and turns a real violation into a passing check.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence

from .lattice import Boundary, Coord, LatticeMemory

__all__ = ["MMU", "AliasingError"]


class AliasingError(ValueError):
    """Raised when two coordinates are bound to the same frame, or vice versa."""


class MMU(LatticeMemory):
    """Lattice memory with an explicit page directory.

    Frames are the addressable units of the machine; coordinates are the
    mathematical objects. The mapping between them is total and injective.
    """

    __slots__ = ("page_directory", "_frame_owner")

    def __init__(self, dims: int = 4) -> None:
        super().__init__(dims=dims)
        self.page_directory: Dict[Coord, int] = {}
        self._frame_owner: Dict[int, Coord] = {}

    # ------------------------------------------------------------------
    # mapping
    # ------------------------------------------------------------------

    def map(self, coord: Sequence[int], frame: int) -> None:
        """Bind ``coord`` to ``frame``. Rejects any aliasing."""
        coord = self._check_coord(coord)
        frame = int(frame)
        if frame < 0:
            raise ValueError("frame identifiers must be non-negative")

        existing_frame = self.page_directory.get(coord)
        if existing_frame is not None and existing_frame != frame:
            raise AliasingError(
                f"coordinate {coord} is already bound to frame {existing_frame}"
            )

        owner = self._frame_owner.get(frame)
        if owner is not None and owner != coord:
            raise AliasingError(
                f"frame {frame} already belongs to coordinate {owner}"
            )

        self.page_directory[coord] = frame
        self._frame_owner[frame] = coord

    def frame_of(self, coord: Sequence[int]) -> Optional[int]:
        return self.page_directory.get(tuple(coord))

    def coord_of(self, frame: int) -> Optional[Coord]:
        return self._frame_owner.get(int(frame))

    def mapped_frames(self) -> int:
        return len(self.page_directory)

    def check_integrity(self) -> bool:
        """True when the directory is injective in both directions."""
        if len(set(self.page_directory.values())) != len(self.page_directory):
            return False
        for coord, frame in self.page_directory.items():
            if self._frame_owner.get(frame) != coord:
                return False
        return True

    # ------------------------------------------------------------------
    # storage is the same as the base lattice; mapping is advisory metadata
    # ------------------------------------------------------------------

    def copy(self) -> "MMU":
        clone = MMU(self.dims)
        clone._cells = dict(self._cells)
        clone.page_directory = dict(self.page_directory)
        clone._frame_owner = dict(self._frame_owner)
        return clone

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"MMU(dims={self.dims}, cells={len(self._cells)}, "
            f"frames={len(self.page_directory)})"
        )
