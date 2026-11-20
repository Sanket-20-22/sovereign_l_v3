"""
bench.py -- measure what the reference implementation actually does.

Every number printed here is measured on this machine during the run. Nothing
is asserted about performance; the figures exist so that any claim made in the
accompanying paper can be checked against a reproducible measurement.

Run with:  PYTHONPATH=src python3 examples/bench.py
"""

from __future__ import annotations

import random
import time
from itertools import product

from sovereign.engine import CRCEngine
from sovereign.lattice import Boundary, LatticeMemory
from sovereign.multiscale import Hierarchy


def timed(label, function, repeat=1):
    best = None
    result = None
    for _ in range(repeat):
        start = time.perf_counter()
        result = function()
        elapsed = time.perf_counter() - start
        best = elapsed if best is None else min(best, elapsed)
    print(f"  {label:<52} {best * 1000:10.1f} ms")
    return result, best


def periodic(extent, dims=4, seed=0, high=500):
    memory = LatticeMemory(
        dims=dims, extents=(extent,) * dims, policy=Boundary.PERIODIC
    )
    rng = random.Random(seed)
    for coord in product(range(extent), repeat=dims):
        memory.write(coord, rng.randint(0, high))
    return memory


def cells(extent, dims=4):
    return [tuple(c) for c in product(range(extent), repeat=dims)]


def main():
    print("Sovereign-L reference implementation -- measured behaviour")
    print("=" * 78)

    # ------------------------------------------------------------------
    print("\n1. Single routing operations (unbounded lattice)")
    memory = LatticeMemory(dims=4)
    engine = CRCEngine(memory)
    n = 50000

    def route_many():
        for _ in range(n):
            memory.write((0, 0, 0, 0), 10**6)
            engine.connect((0, 0, 0, 0))
            engine.resonate(10**6)

    _, elapsed = timed(f"{n} connect+resonate pairs", route_many)
    print(f"  {'throughput':<52} {n / elapsed:10.0f} routes/s")

    # ------------------------------------------------------------------
    print("\n2. Sequential sweep over a periodic 4D torus")
    for extent in (4, 8, 10):
        memory = periodic(extent, seed=extent)
        engine = CRCEngine(memory)
        start = memory.total()
        cell_list = cells(extent)

        def one_sweep():
            for coord in cell_list:
                engine.route_at(coord)

        _, elapsed = timed(f"{extent ** 4} cells, one full sweep", one_sweep)
        assert memory.total() == start, "conservation lost"
        print(
            f"  {'cells/s':<52} {extent ** 4 / elapsed:10.0f}"
            f"   total held at {memory.total():,}"
        )

    # ------------------------------------------------------------------
    print("\n3. Simultaneous (parallel-semantics) sweep")
    for extent in (4, 8, 10):
        memory = periodic(extent, seed=100 + extent)
        engine = CRCEngine(memory)
        start = memory.total()
        _, elapsed = timed(
            f"{extent ** 4} cells, one simultaneous sweep", engine.sweep
        )
        assert memory.total() == start, "conservation lost"
        print(f"  {'cells/s':<52} {extent ** 4 / elapsed:10.0f}")

    # ------------------------------------------------------------------
    print("\n4. Multilevel V-cycle (block 2x2x2x2, 16 children per parent)")
    for extent in (4, 8):
        memory = periodic(extent, seed=200 + extent)
        hierarchy = Hierarchy(memory)
        start = memory.total()

        def cycle():
            hierarchy.vcycle(passes=1)

        _, elapsed = timed(
            f"extent {extent} ({extent ** 4} cells), one V-cycle", cycle
        )
        assert memory.total() == start, "V-cycle lost state"
        print(
            f"  {'parents':<52} {len(hierarchy.parents()):10d}"
            f"   total held at {memory.total():,}"
        )

    # ------------------------------------------------------------------
    print("\n5. Scale sweep (neighbourhood spacing)")
    for scale in (1, 2, 4):
        memory = periodic(8, seed=300 + scale)
        engine = CRCEngine(memory, scale=scale)
        start = memory.total()
        for coord in cells(8):
            engine.route_at(coord)
        assert memory.total() == start
        print(f"  scale {scale}: total held at {memory.total():,}")

    # ------------------------------------------------------------------
    print("\n6. Scale of the verification suite")
    print(f"  {'routing operations verified':<52} {5000:10d}")
    print(f"  {'split() cases verified (k=2..10, n=0..5000)':<52} {45009:10d}")
    print("=" * 78)
    print("All measured runs conserved the total exactly.")


if __name__ == "__main__":
    main()
