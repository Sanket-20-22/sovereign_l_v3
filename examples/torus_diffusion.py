"""
torus_diffusion.py -- repeated conservative transport on a periodic 4D torus.

This is the workload the operator actually performs: every cell hands its
state to its eight axial neighbours, and the total never changes. The field
relaxes towards uniformity; it is a smoothing operator, not a solver.

Run with:  PYTHONPATH=src python3 examples/torus_diffusion.py
"""

import random
from itertools import product

from sovereign import Boundary, CRCEngine, LatticeMemory

EXTENT = 6
STEPS = 12

memory = LatticeMemory(
    dims=4, extents=(EXTENT,) * 4, policy=Boundary.PERIODIC
)
engine = CRCEngine(memory)
rng = random.Random(2026)

# seed a hot block at the centre, everything else cold
for coord in product(range(EXTENT), repeat=4):
    hot = all(2 <= c <= 3 for c in coord)
    memory.write(coord, 800 if hot else 20)

start = memory.total()
print(f"lattice {EXTENT}^4 = {EXTENT ** 4} cells, total state {start:,}")
print(f"{'step':>5} {'total':>10} {'min':>7} {'max':>7} {'spread':>8}")

for step in range(STEPS + 1):
    values = list(memory._cells.values())
    print(
        f"{step:>5} {memory.total():>10,} {min(values):>7} {max(values):>7}"
        f" {max(values) - min(values):>8}"
    )
    if step < STEPS:
        engine.sweep()

print()
print(f"total unchanged: {memory.total() == start}")
print("the spread collapses; the total does not move.")
