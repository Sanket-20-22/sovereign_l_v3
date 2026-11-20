# Architecture

## Module map

```
src/sovereign/
    lattice.py      sparse integer state; boundary policies; de-duplicating totals
    engine.py       the routing operator; CONNECT / RESONATE / COLLAPSE; sweeps
    multiscale.py   restriction, prolongation, V-cycle
    mmu.py          coordinate <-> frame translation, injective
    isa.py          opcode table, operand widths, encoding helpers
    assembler.py    two-pass assembler with labels and range checks
    vm.py           fetch-decode-execute machine
```

Dependency order is strictly downwards: `vm` depends on `engine`, `engine` on
`lattice`. Nothing imports upwards, and there are no cycles.

## The routing operator

For neighbourhood size `k` and quantity `n`:

```
(q, r) = divmod(n, k)
R_i(n) = q + 1   if i < r
         q       otherwise

Omega_source'   = Omega_source - n
Omega_dest_i'   = Omega_dest_i + R_i(n)
```

`k = 2 * dims`, so a 4-dimensional lattice uses eight neighbours and a
2-dimensional lattice uses four. The number eight is a consequence of the
dimension, not a constant of the framework.

## Invariants held by the code

| Invariant | Where enforced |
|---|---|
| `sum(R(n)) == n` | `engine.split` |
| the local scope total is unchanged by routing | `engine.collapse` |
| the global total is unchanged by a sweep | `engine.sweep` |
| a parent's value equals the sum of its children | `multiscale.restrict` |
| a coordinate owns exactly one frame, and vice versa | `mmu.map` |
| cell values are non-negative integers | `lattice.write` |
| every assembler operand fits its declared width | `assembler._encode_operand` |

## Boundary policies

`LatticeMemory` resolves every coordinate through one of three policies.

| Policy | Behaviour | Use |
|---|---|---|
| `UNBOUNDED` | coordinates used as given | mathematics; sparse problems |
| `PERIODIC` | wrap modulo `extents` | finite domains without walls; torus tests |
| `ABSORBING` | outside the domain is not part of the lattice; writing raises | problems with a real boundary |

The policy is a modelling decision and is never inferred. A finite scheme
without a declared policy leaks state, which is why the multiscale module
refuses to build a hierarchy over an unbounded lattice.

## Update semantics

Two orders are provided and both conserve.

**Sequential** (`route_at` per cell): each cell is routed in turn, so later
cells see the state left by earlier ones. This is Gauss-Seidel-like and depends
on the visiting order.

**Simultaneous** (`sweep`): every cell reads the old state and writes into a
new one. The result is independent of visiting order, which is what a parallel
machine would do. Verified by sweeping a lattice forwards and backwards and
comparing the resulting state cell by cell.

## Instruction set (v3)

Little-endian, variable length. `s8` is a signed byte, `u8` unsigned byte,
`u16` unsigned 16-bit little-endian.

| Code | Mnemonic | Operands | Length | Effect |
|---|---|---|---|---|
| `0x00` | `NOP` | — | 1 | nothing |
| `0x01` | `LOAD_VAL` | `u16` | 3 | `AL <- imm` |
| `0x02` | `DIV_MOD_K` | — | 1 | `AL, R <- divmod(AL, k)` |
| `0x03` | `ADD_REG` | `s8` | 2 | `AL <- AL + imm` |
| `0x04` | `SUB_REG` | `s8` | 2 | `AL <- AL - imm` |
| `0x05` | `MMU_MAP` | `s8 s8 s8 s8 u16` | 7 | bind coordinate to frame |
| `0x06` | `STORE_CELL` | `s8 s8 s8 s8` | 5 | `cell <- AL` |
| `0x07` | `FETCH_CELL` | `s8 s8 s8 s8` | 5 | `AL <- cell` |
| `0x08` | `SET_SCALE` | `u8` | 2 | neighbourhood spacing |
| `0x09` | `SET_EXTENT` | `s8 s8 s8 s8` | 5 | periodic extents; all-zero = unbounded |
| `0x0A` | `CONNECT` | `s8 s8 s8 s8` | 5 | bind neighbourhood of an explicit centre |
| `0x0B` | `RESONATE` | — | 1 | route `AL` from the centre |
| `0x0C` | `COLLAPSE` | — | 1 | verify the invariant; trap on failure |
| `0x0D` | `SWEEP` | — | 1 | simultaneous update of all mapped cells |
| `0x0E` | `JMP` | `u16` | 3 | unconditional jump |
| `0x0F` | `JMP_NZ` | `u16` | 3 | jump when `AL != 0` |
| `0xFF` | `HALT` | — | 1 | stop |

Address space: 65,536 bytes of program, 65,536 frames, coordinates in
`[-128, 127]` per axis.

`COLLAPSE` is the architectural feature worth noting: the conservation check
sits in the instruction stream and stops the machine, rather than being left to
the caller.

## Design decisions and why

**Dimension is a parameter, not a constant.** The earlier code described
four-dimensional axial routing while implementing two-dimensional Moore
neighbourhoods. Making `dims` explicit makes that class of mistake impossible:
the neighbour count is derived from the dimension, so the documentation and the
code cannot disagree.

**Totals de-duplicate.** A conservation check that sums a list of coordinates
is wrong the moment two entries name the same cell. De-duplicating at the
memory level means every caller gets a correct total without having to think
about it.

**The MMU rejects aliasing.** Allowing two coordinates to share a frame makes
the same cell appear twice in a total, which turns a real violation into a
passing check. Rejecting the mapping is the safe direction.

**Scale changes invalidate the connection.** A topology and a baseline that
were recorded at different spacings are not comparable, so changing the scale
clears both.

**The multiscale cycle verifies itself.** `vcycle` compares the fine total
before and after and raises when it moved. A silent loss of state is the
failure mode the module exists to prevent, so it is checked rather than
assumed.
