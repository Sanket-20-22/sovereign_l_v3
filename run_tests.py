#!/usr/bin/env python3
"""
run_tests.py -- run the verification suite and write a results log.

    python3 run_tests.py                # run everything, print a summary
    python3 run_tests.py --log FILE     # also write a markdown results log

No third-party test runner is required; this uses the standard library.
"""

from __future__ import annotations

import argparse
import io
import os
import platform
import sys
import time
import unittest
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tests"))


def build_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in sorted(os.listdir(os.path.join(ROOT, "tests"))):
        if name.startswith("test_") and name.endswith(".py"):
            module = name[:-3]
            suite.addTests(loader.loadTestsFromName(module))
    return suite


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default=None, help="write a markdown log here")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    suite = build_suite()
    stream = io.StringIO()
    runner = unittest.TextTestRunner(
        stream=stream, verbosity=1 if args.quiet else 2
    )
    started = time.perf_counter()
    result = runner.run(suite)
    elapsed = time.perf_counter() - started

    if not args.quiet:
        print(stream.getvalue())

    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total - failures - errors - skipped

    print("=" * 70)
    print(f"tests run : {total}")
    print(f"passed    : {passed}")
    print(f"failed    : {failures}")
    print(f"errors    : {errors}")
    print(f"skipped   : {skipped}")
    print(f"duration  : {elapsed:.2f} s")
    print(f"verdict   : {'PASS' if result.wasSuccessful() else 'FAIL'}")
    print("=" * 70)

    if args.log:
        lines = [
            "# Verification results",
            "",
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            f"- Python: {platform.python_version()}",
            f"- Platform: {platform.system()} {platform.machine()}",
            f"- Tests run: {total}",
            f"- Passed: {passed}",
            f"- Failed: {failures}",
            f"- Errors: {errors}",
            f"- Duration: {elapsed:.2f} s",
            f"- Verdict: {'PASS' if result.wasSuccessful() else 'FAIL'}",
            "",
            "Reproduce with:",
            "",
            "```",
            "python3 run_tests.py --log docs/TEST_RESULTS.md",
            "```",
            "",
        ]
        if not result.wasSuccessful():
            lines.append("## Failures")
            lines.append("")
            for case, trace in result.failures + result.errors:
                lines.append(f"### {case}")
                lines.append("")
                lines.append("```")
                lines.append(trace.strip())
                lines.append("```")
                lines.append("")
        with open(args.log, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        print(f"log written to {args.log}")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
