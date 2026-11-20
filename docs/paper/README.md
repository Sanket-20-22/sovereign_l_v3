# Working paper

| File | Contents |
|---|---|
| `working_paper.tex` | LaTeX source |
| `working_paper.pdf` | compiled, 10 pages |

Rebuild with:

```bash
cd docs/paper
pdflatex working_paper.tex
pdflatex working_paper.tex    # second pass resolves cross-references
```

The paper's tables cite two commands from the repository root:

```bash
python3 run_tests.py --log docs/TEST_RESULTS.md   # Table 1
PYTHONPATH=src python3 examples/bench.py          # Table 2
```

Every number in the paper is produced by one of those two commands.
