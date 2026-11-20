# Scope, limitations and future work

This document is the boundary of the project. Anything not listed in §1 is not
claimed; anything in §2 must not appear in a paper, a README or a talk without
first being demonstrated in this repository.

---

## 1. What is established

Each item below is enforced by a test in `tests/` and can be reproduced with
`python3 run_tests.py`.

**1.1 The routing operator.** For a neighbourhood of `k` ordered destinations
and a non-negative integer `n`, the shares `R_i(n) = q + [i < r]` where
`(q, r) = divmod(n, k)` satisfy:

- exact conservation, `sum_i R_i(n) = n`;
- bounded imbalance, `max_i R_i - min_i R_i <= 1`;
- each share is `q` or `q + 1`, with exactly `r` shares equal to `q + 1`;
- determinism for a fixed ordering;
- translation invariance, `split(n + k, k) = split(n, k) + 1` elementwise.

Verified exhaustively for `k = 2..10` and `n = 0..5000`, and by randomised
testing for `n` up to 10^6.

**1.2 Conservation of the local state under routing.** The source loses exactly
what the destinations gain, so the total over the nine-cell scope is invariant.
Verified over 5,000 randomised routing operations.

**1.3 Conservation over a whole lattice.** Repeated full sweeps of a periodic
4-dimensional torus preserve the global total exactly, at extents 4, 8 and 10
(256, 4,096 and 10,000 cells), at neighbourhood spacings 1, 2 and 3, and under
both sequential and simultaneous update semantics.

**1.4 Multilevel conservation.** Restriction (parent = sum of children) and
prolongation (children = split of parent) are exact on integers, so a V-cycle
that restricts, routes at the coarse level and prolongs returns the fine
lattice to exactly the same total. Verified for repeated cycles at extents 4
and 8.

**1.5 Boundary behaviour.** On a lattice small enough for two neighbours to
coincide, shares accumulate in the shared cell and the conservation scope is
de-duplicated, so the invariant still holds. Verified on a 2^4 torus, where
eight neighbours collapse to four distinct cells.

**1.6 A working assembler and machine.** A 17-mnemonic ISA, a two-pass
assembler with range-checked operands and 16-bit jump targets, and a
fetch-decode-execute machine that executes assembled programs, including a
trapping conservation check. Verified end to end.

**1.7 Integer exactness.** All arithmetic is integer arithmetic. There is no
floating-point path in the implementation, so rounding behaviour is not defined
and not claimed.

---

## 2. What is explicitly not claimed

These were claimed in earlier material and are withdrawn. They are not
weaknesses of the implementation; they are claims the implementation never
supported.

**2.1 No performance claim of any kind.** There is no measured comparison
against a CPU, GPU, TPU or any other architecture. The earlier figures of
87.50%, 89.47% and 94.44% "bus reduction" were ratios of hand-assigned
transaction counters, not measurements of memory traffic, and they are
withdrawn. `examples/bench.py` reports throughput of this Python reference
implementation only, which is not a performance claim about any architecture.

**2.2 No hardware claim.** This is a software reference model. No RTL, no
synthesis, no timing, no area, no power. The ISA is a specification for a
machine that could be built; it is not evidence that one has been.

**2.3 No physical interpretation.** The lattice is a data structure. Nothing
here establishes that it models spacetime, a physical field, energy,
thermodynamics or entropy. The imaginary-mass modes and the
conscious/superconscious/subconscious decomposition in the earlier thesis have
no counterpart in this code and are withdrawn.

**2.4 No claim of computational superiority.** The operator converges to a
uniform state under repeated application. It is a conservative smoothing
primitive, not a solver, and it does not replace a numerical method for any
physical problem.

**2.5 No claim of novelty for the routing rule.** `n = kq + r` with the
remainder distributed to the first `r` destinations is the largest-remainder
rule, known in apportionment literature since the eighteenth century. What may
be novel is the characterisation of the rule family (§4.2), not the rule.

**2.6 No application claim.** No climate, atmospheric, urban or economic model
is validated here. The examples are demonstrations of conservation, not
simulations of anything.

---

## 3. Defects fixed relative to the earlier prototype

Recorded so that anyone comparing versions understands what changed and why.

| # | Defect | Consequence | Fix |
|---|---|---|---|
| 3.1 | Neighbour definition used four orthogonal plus four diagonal cells in a 2D grid while the documentation described eight axial neighbours in Z^4 | the simulation contradicted its own specification | neighbours are now exactly `+/- s*e_i`; dimension is a parameter and `k = 2*dims` follows from it |
| 3.2 | Conservation scope summed the raw neighbour list | on a small periodic lattice, coincident neighbours were counted twice and the invariant reported a false failure | scope is de-duplicated; shares accumulate in the shared cell |
| 3.3 | The MMU permitted two coordinates to share a frame | the same cell counted twice in a total, so a real violation could pass | the mapping is injective in both directions; aliasing raises |
| 3.4 | The `CONNECT` instruction hardcoded the origin | a program could not route from any cell but `(0,0,0,0)` | `CONNECT` carries an explicit centre |
| 3.5 | Jump targets were one byte | programs were capped at 256 bytes | 16-bit targets; programs up to 65,536 bytes |
| 3.6 | Coordinates were unsigned bytes | negative lattice coordinates were unrepresentable | signed-byte coordinates, range-checked |
| 3.7 | A partial sweep dropped cells whose routed amount was zero | silent loss of state | the unrouted remainder is always retained |
| 3.8 | Scale could change between CONNECT and RESONATE without notice | routing used a stale topology against a stale baseline | changing scale invalidates the connection |
| 3.9 | Multiscale module returned a distribution map that no caller stored | the "multiscale" run computed nothing | replaced by an explicit restriction/prolongation/V-cycle hierarchy with an invariant check |
| 3.10 | Two copies of the same 400-line module, two `__main__` blocks in one file, committed logs that no longer reproduced | ambiguity about which file was current | single module per concern, one entry point each, logs generated by the test runner |

---

## 4. Future work

Separated by how much evidence already exists for it. The first group is
reachable from this repository; the second is speculative and should be
labelled as such in any document.

### 4.1 Plausible, with a defined next step

**Classification of the rule family.** Characterise all routing rules
`R: N -> N^k` that are conservative, balanced to within one, deterministic and
translation invariant, and show they are exactly the orderings of the
largest-remainder rule. This turns a description into a theorem and is the
strongest available contribution. Next step: `docs/ROADMAP.md` Phase 2.2.

**Conservation under simultaneous update.** The implementation demonstrates it;
the proof should be written out, including the boundary cases.

**Boundary-condition theory.** Periodic, reflecting and absorbing boundaries
each interact differently with the invariant. The absorbing case currently
refuses rather than redistributes, which is a design choice that deserves
analysis.

**Convergence of repeated sweeps.** The measured spread decreases monotonically
in `examples/torus_diffusion.py`. The rate, and the conditions under which the
uniform state is reached exactly rather than asymptotically, are open.

**A native implementation and an honest baseline.** The current reference is
Python and its throughput is irrelevant to any architectural question. A C or
Rust kernel compared against a cache-blocked integer baseline, measured with
hardware counters, would settle the performance question one way or the other.
Next step: Phase 3, with its kill criterion.

### 4.2 Speculative — do not present as results

**An FPGA implementation of the scatter-add and invariant comparator.** The
arithmetic is gate-friendly: a 3-bit shift, a one-hot mask and eight adders for
the routing; a nine-input adder tree and a comparator for the check. Whether
that beats a general-purpose core on any real workload is unknown and is
exactly what Phase 4 is for.

**A distributed variant.** The invariant check is a natural safety property for
a replicated state machine. Whether it is useful there depends on whether
conservation is a property anyone needs, which is an empirical question about
users, not about mathematics.

**Higher-dimensional and non-cubic neighbourhoods.** The operator is defined for
any `k`; lattices other than Z^d with axial connectivity have not been studied
here.

---

## 5. How to keep this honest

Three rules, applied to every future document:

1. If it is not in §1, it is not established.
2. If it contradicts §2, it is withdrawn.
3. Every number in a paper must be reproducible by a command in this
   repository, and the command must be named next to the number.
