# Work chart

The plan from this point forward. Every phase has a deliverable, an effort
estimate, and a gate that decides whether the next phase is worth starting.
The gates matter more than the phases: they are the points at which the
project is allowed to stop.

Status as of 2026-11-20: **Phase 0 complete.** The reference implementation in
this repository is the output of that phase.

---

## Phase 0 — Consolidation and correctness (complete)

| Item | Output |
|---|---|
| Remove duplicate and superseded code | one package, no duplicate files |
| Fix the four defects found in the earlier prototype | see `docs/SCOPE.md` §3 |
| Establish a test suite with a reproducible log | 88 tests, `docs/TEST_RESULTS.md` |
| Separate what is verified from what is claimed | `docs/SCOPE.md` |

Effort spent: consolidated from roughly 4,800 lines across two repositories
into about 1,300 lines with a test suite.

**Exit criteria met:** every stated property has a test; no module asserts a
performance number; the conservation invariant is enforced in code rather than
in prose.

---

## Phase 1 — Correct the record (2–3 weeks)

The earlier manuscript was submitted while the implementation still had the
defects now fixed. That submission should be withdrawn or replaced rather than
left to be reviewed against claims the code no longer makes.

| # | Task | Deliverable | Effort |
|---|---|---|---|
| 1.1 | Withdraw or supersede the current submission | correspondence with the editor | 1 day |
| 1.2 | Revise the working paper to match this implementation | `docs/paper/working_paper.pdf` | 1 week |
| 1.3 | Deposit the revised paper and this repository | Zenodo DOI, tagged release | 2 days |
| 1.4 | Remove or relabel every unverified figure in older material | corrected thesis and whitepaper | 1 week |

**Gate 1:** the published record contains no number that the repository cannot
reproduce. If this cannot be done, nothing later matters.

---

## Phase 2 — Theory (4–6 weeks)

The implementation proves properties by testing. Three of them should be
proved by argument, because they are the ones a referee will ask about.

| # | Task | Deliverable | Effort |
|---|---|---|---|
| 2.1 | Conservation under simultaneous update | theorem + proof | 1 week |
| 2.2 | Classification: which routing rules satisfy conservation, bounded imbalance, determinism and translation invariance | theorem + proof — this is the paper's real contribution | 2–3 weeks |
| 2.3 | Boundary-condition theory: periodic, reflecting, absorbing, and what each does to the invariant | section + proofs | 1 week |
| 2.4 | Behaviour of repeated sweeps: convergence to the uniform state, and the rate | analysis, with the measured spread as evidence | 1–2 weeks |

**Gate 2:** at least one result is a theorem rather than a test. Without 2.2 the
work remains a description of a known apportionment rule.

---

## Phase 3 — Honest performance (3–4 weeks)

The only performance question that matters: does an integer formulation of this
kind beat a well-tuned integer baseline on a real workload? Everything else is
measurement theatre.

| # | Task | Deliverable | Effort |
|---|---|---|---|
| 3.1 | Implement the operator in C or Rust | `native/` reference kernel | 1 week |
| 3.2 | Build a fair baseline: same problem, integer arithmetic, cache-blocked | baseline implementation | 1 week |
| 3.3 | Measure real memory traffic with hardware counters | results table, method stated | 1 week |
| 3.4 | Report throughput, bandwidth and energy per update | benchmark report | 1 week |

**Gate 3 (kill criterion):** if the integer formulation does not beat the
baseline on any real workload, stop the accelerator line of work and publish
the discrete mathematics on its own. This is a legitimate and respectable
outcome; the mathematics stands without the hardware story.

---

## Phase 4 — Hardware prototype (3–6 months)

Only entered if Gate 3 passes.

| # | Task | Deliverable | Effort |
|---|---|---|---|
| 4.1 | RTL for the scatter-add unit: 3-bit shift, one-hot remainder mask, eight adders | Verilog module + testbench | 4–6 weeks |
| 4.2 | RTL for the invariant comparator: nine-input adder tree against a baseline register, trap output | Verilog module | 2 weeks |
| 4.3 | Address generator with a programmable stride register | Verilog module | 2 weeks |
| 4.4 | Integrate on an FPGA (Artix-7 or ECP5) | synthesised design, timing report | 6–8 weeks |
| 4.5 | Measure Fmax, cells/s, LUT/FF/BRAM use, energy per update | hardware results section | 3 weeks |

**Gate 4:** the prototype must beat the Phase 3 software baseline on
throughput per watt, at a stated problem size. If it only matches it, the
architectural claim fails and the honest write-up says so.

---

## Phase 5 — One application, done properly (parallel with 4, 3 months)

Pick **one** domain. The earlier material named planetary climate modelling,
which is not credible for a first application and should be dropped. Realistic
candidates, in ascending order of difficulty:

| Candidate | Why it fits | Risk |
|---|---|---|
| Load balancing / apportionment | the operator is exactly the largest-remainder rule | low novelty — it is a known method |
| Replicated state machines with a conservation invariant | COLLAPSE is a natural safety check | needs a distributed story |
| Integer lattice Boltzmann | conservative by construction, real physics | hard to beat mature codes |
| Discrete-event simulation of resource flow | integer states are native | narrow audience |

| # | Task | Deliverable | Effort |
|---|---|---|---|
| 5.1 | Choose one domain and one baseline | written justification | 1 week |
| 5.2 | Build the workload and the comparison | benchmark harness | 4 weeks |
| 5.3 | Write the result, including a negative result | application section | 3 weeks |

**Gate 5:** someone outside the project finds the result useful. If not, the
work is a contribution to discrete mathematics and should be presented as one.

---

## Phase 6 — Publication (after 4 and 5)

| # | Task | Deliverable |
|---|---|---|
| 6.1 | Single paper: operator, theorems, reference implementation, hardware numbers, one application | manuscript |
| 6.2 | Artifact: tagged release, one-command reproduction, test log | archived repository |
| 6.3 | Venue choice matched to the actual contribution | submission |

Venue guidance: with theorems and hardware numbers, a systems or architecture
venue is realistic. With only the routing construction, a discrete-mathematics
or cellular-automata journal is the right home. The earlier choice of *Discrete
Applied Mathematics* was reasonable for the mathematics and wrong for the
physics framing.

---

## Dependency graph

```
Phase 0 (done)
   |
   +--> Phase 1 (correct the record) --> Gate 1
   |
   +--> Phase 2 (theory) --> Gate 2
   |        |
   +--------+--> Phase 3 (performance) --> Gate 3
                                            |
                                            +--> Phase 4 (hardware) --> Gate 4
                                            |
                                            +--> Phase 5 (application) --> Gate 5
                                                     |
                                                     +--> Phase 6 (publication)
```

Phase 1 and Phase 2 are independent and can run together. Phases 4 and 5 are
independent of each other and both depend on Gate 3.

---

## Risk register

| Risk | Likelihood | Consequence | Mitigation |
|---|---|---|---|
| The operator is not novel enough for a strong venue | high | rejection | Phase 2.2 classification theorem; submit the mathematics separately |
| Integer formulation loses to tuned floating point on real workloads | medium | accelerator claim fails | Gate 3 exists to find this out early and cheaply |
| FPGA work exceeds available time or equipment | medium | no hardware result | Phase 3 software numbers still support a paper |
| Scope creep back into physics claims | high | credibility loss | `docs/SCOPE.md` §2 is the fixed boundary; every new claim is checked against it |
| Single-author bandwidth | high | phases slip | gates are sequential; nothing is lost by stopping at a gate |

---

## What "done" looks like

A repository someone else can clone, run in one command, and reproduce every
number in a paper — where the paper claims only what the repository
demonstrates. That is the whole target. It is reachable from here.
