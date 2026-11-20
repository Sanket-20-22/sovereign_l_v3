"""
routing_demo.py -- the routing operator on a single neighbourhood.

Shows the three operations, the routing vector, and the invariant check.
Run with:  PYTHONPATH=src python3 examples/routing_demo.py
"""

from sovereign import CRCEngine, LatticeMemory, split

print("Routing vector for n = 27 with k = 8:")
print(" ", split(27, 8))
print(" 27 = 8*3 + 3, so three destinations receive 4 and five receive 3.")
print()

memory = LatticeMemory(dims=4)
engine = CRCEngine(memory)

memory.write((0, 0, 0, 0), 27)
engine.connect((0, 0, 0, 0))

print(f"CONNECT  centre={(0, 0, 0, 0)}  baseline={engine.baseline}")
print(f"  neighbours: {engine.links}")
print()

vector = engine.resonate(27)
print(f"RESONATE 27 -> {vector}")
print(f"  centre now holds {memory.read((0, 0, 0, 0))}")
for link, share in zip(engine.links, vector):
    print(f"  {link} += {share}  -> {memory.read(link)}")
print()

print(f"COLLAPSE  expected {engine.baseline}, observed {engine.local_total()}"
      f"  ->  {'PASS' if engine.collapse() else 'FAIL'}")
print()

print("Injecting 5 units by hand to show the check is not a rubber stamp:")
memory.add((1, 0, 0, 0), 5)
print(f"  COLLAPSE -> {'PASS' if engine.collapse() else 'FAIL'}"
      f"  (observed {engine.local_total()})")
