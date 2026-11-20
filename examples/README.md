# Examples

Run any of these from the repository root with `PYTHONPATH=src`.

| File | What it shows |
|---|---|
| `routing_demo.py` | the three operations on one neighbourhood, and the check firing on an injected fault |
| `torus_diffusion.py` | repeated conservative transport on a periodic 4D torus; the spread collapses, the total does not move |
| `multigrid_vcycle.py` | restriction, coarse routing and prolongation; also the leak that happens without a boundary policy |
| `bench.py` | measured timings of this Python reference implementation |

`bench.py` measures the reference implementation only. It is not a benchmark
against any other system, and its numbers say nothing about what a native
implementation or a dedicated circuit would achieve.
