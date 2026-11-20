"""
multigrid_vcycle.py -- restriction, coarse routing and prolongation.

Demonstrates that a two-level cycle returns the fine lattice to exactly the
same total, and that the same code fails loudly if the coarse level is left
without a boundary policy.

Run with:  PYTHONPATH=src python3 examples/multigrid_vcycle.py
"""

import random
from itertools import product

from sovereign import Boundary, CRCEngine, Hierarchy, LatticeMemory

EXTENT = 4

memory = LatticeMemory(
    dims=4, extents=(EXTENT,) * 4, policy=Boundary.PERIODIC
)
rng = random.Random(7)
for coord in product(range(EXTENT), repeat=4):
    memory.write(coord, rng.randint(0, 200))

hierarchy = Hierarchy(memory)  # block 2x2x2x2 -> 16 children per parent
start = memory.total()

print(f"fine lattice {EXTENT}^4 = {EXTENT ** 4} cells")
print(f"parents {len(hierarchy.parents())}, children per parent {hierarchy.k}")
print(f"fine total before: {start:,}")
print()

hierarchy.restrict()
print(f"after restriction, coarse total: {hierarchy.coarse_total():,}")
print(f"  matches fine total: {hierarchy.coarse_total() == start}")

for passes in (1, 2, 4):
    hierarchy.vcycle(passes=passes)
    print(
        f"after a V-cycle with {passes} coarse pass(es): "
        f"fine total {memory.total():,}  held: {memory.total() == start}"
    )

print()
values = sorted(memory._cells.values())
print(f"field range after cycles: {values[0]} .. {values[-1]}")
print("state moved between cells; the total did not move at all.")
print()

# ---------------------------------------------------------------------
# the failure mode this module exists to prevent
# ---------------------------------------------------------------------
print("Now the same cycle with the coarse level left unbounded:")
unbounded = LatticeMemory(
    dims=4, extents=(EXTENT,) * 4, policy=Boundary.PERIODIC
)
for coord in product(range(EXTENT), repeat=4):
    unbounded.write(coord, 10)

leaky = Hierarchy(unbounded)
leaky.coarse_memory = LatticeMemory(dims=4)      # no boundary at all
leaky.coarse_engine = CRCEngine(leaky.coarse_memory)

before = unbounded.total()
try:
    leaky.vcycle()
except AssertionError as error:
    print(f"  V-cycle refused: {error}")
print(f"  total before {before:,}, after {unbounded.total():,}")
print("  routing without a boundary policy invents cells nobody owns;")
print("  the cycle reports it instead of hiding it.")
