#!/usr/bin/env python3
"""
Urmom Lang Test Runner (urm-test)
Discovers and runs test files.

Usage:
    urm-test [path]           Run tests (default: tests/)
    urm-test --verbose        Show detailed output
    urm-test --filter <name>  Run only tests matching name
"""

import os
import sys
import time
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lexer import Lexer
from src.parser import Parser
from src.evaluator import Evaluator, ThrowSignal, UrmString, UrmBool, UrmNone, URM_NONE


class TestResult:
    def __init__(self, name: str, passed: bool, error: str = "", duration: float = 0.0):
        self.name = name
        self.passed = passed
        self.error = error
        self.duration = duration


class TestRunner:
    def __init__(self, verbose: bool = False, filter_pattern: str = ""):
        self.verbose = verbose
        self.filter_pattern = filter_pattern
        self.results: list[TestResult] = []
        self.passed = 0
        self.failed = 0
        self.errors = 0

    def discover_tests(self, path: str) -> list[str]:
        """Find all test files."""
        test_files = []
        if os.path.isfile(path):
            if path.endswith('.urm') or 'test' in os.path.basename(path).lower():
                test_files.append(path)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for f in sorted(files):
                    if f.endswith('.urm') or 'test' in f.lower():
                        test_files.append(os.path.join(root, f))
        return test_files

    def run_test_file(self, filepath: str) -> list[TestResult]:
        """Run all tests in a single file."""
        results = []
        try:
            with open(filepath, 'r') as f:
                source = f.read()
        except Exception as e:
            results.append(TestResult(filepath, False, f"Cannot read file: {e}"))
            return results

        try:
            lexer = Lexer(source, filepath)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            program = parser.parse()

            # Find test functions (those starting with "test_")
            test_fns = []
            for decl in program.declarations:
                if hasattr(decl, 'name') and decl.name.startswith('test_'):
                    if self.filter_pattern and self.filter_pattern not in decl.name:
                        continue
                    test_fns.append(decl.name)

            # Run the whole program (including main() which calls test functions)
            evaluator = Evaluator()
            start = time.time()
            try:
                evaluator.run(program)
                duration = time.time() - start
                if test_fns:
                    for fn_name in test_fns:
                        results.append(TestResult(fn_name, True, duration=duration / len(test_fns)))
                        self.passed += 1
                        if self.verbose:
                            print(f"  ✓ {fn_name}")
                else:
                    results.append(TestResult(filepath, True, duration=duration))
                    self.passed += 1
            except ThrowSignal as e:
                duration = time.time() - start
                msg = e.value.value if isinstance(e.value, UrmString) else str(e)
                if test_fns:
                    # Mark the last test as failed
                    for fn_name in test_fns[:-1]:
                        results.append(TestResult(fn_name, True, duration=duration / len(test_fns)))
                        self.passed += 1
                    results.append(TestResult(test_fns[-1], False, msg, duration))
                    self.failed += 1
                    print(f"  ✗ {test_fns[-1]}: {msg}")
                else:
                    results.append(TestResult(filepath, False, msg, duration))
                    self.failed += 1

        except Exception as e:
            results.append(TestResult(filepath, False, f"Parse error: {e}"))
            self.errors += 1

        return results

    def run(self, path: str = "tests/") -> int:
        """Run all discovered tests."""
        test_files = self.discover_tests(path)
        if not test_files:
            print(f"No test files found in '{path}'")
            return 0

        print(f"Urmom Lang Test Runner")
        print(f"Found {len(test_files)} test file(s)\n")

        start_time = time.time()
        for filepath in test_files:
            print(f"Running: {filepath}")
            self.run_test_file(filepath)
            print()

        total_time = time.time() - start_time
        total = self.passed + self.failed + self.errors

        print("=" * 50)
        print(f"Results: {self.passed} passed, {self.failed} failed, {self.errors} errors")
        print(f"Total: {total} test(s) in {total_time:.3f}s")
        print("=" * 50)

        return 1 if (self.failed + self.errors) > 0 else 0


def run_tests(path: str = "tests/", verbose: bool = False, filter_pattern: str = "") -> int:
    runner = TestRunner(verbose=verbose, filter_pattern=filter_pattern)
    return runner.run(path)


def main():
    """Entry point for urm-test CLI."""
    import argparse
    parser = argparse.ArgumentParser(description='Urmom Lang Test Runner')
    parser.add_argument('path', nargs='?', default='tests/', help='Test file or directory')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--filter', '-f', default='', help='Filter test names')
    args = parser.parse_args()
    sys.exit(run_tests(args.path, args.verbose, args.filter))

if __name__ == '__main__':
    main()
