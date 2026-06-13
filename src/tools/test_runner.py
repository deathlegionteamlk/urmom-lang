"""
Urmom Lang Test Runner
=====================
Discovers and runs test functions from .urm files.
"""

import os
import sys
import time

# Ensure correct import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.lexer import Lexer
from src.parser import Parser
from src.runtime import Evaluator, UrmRuntimeError
from src.ast import FuncDecl


def main():
    """CLI entry point for the test runner."""
    import argparse
    parser = argparse.ArgumentParser(prog='urm-test', description='Urmom Lang Test Runner')
    parser.add_argument('path', nargs='?', default='tests/', help='Test directory')
    args = parser.parse_args()
    
    runner = TestRunner()
    return runner.run(args.path)


class TestRunner:
    """Runs Urmom Lang test files and reports results."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def run(self, path: str) -> int:
        """Run all tests in the given path (file or directory)."""
        print(f"\n{'='*60}")
        print(f"  Urmom Lang Test Runner v0.2.0")
        print(f"{'='*60}\n")
        
        start = time.time()
        test_files = self._discover(path)
        
        if not test_files:
            print(f"No test files found in: {path}")
            return 1
        
        print(f"Found {len(test_files)} test file(s)\n")
        
        for filepath in test_files:
            self._run_file(filepath)
        
        elapsed = time.time() - start
        
        print(f"\n{'='*60}")
        print(f"  Results: {self.passed} passed, {self.failed} failed")
        print(f"  Time: {elapsed:.3f}s")
        print(f"{'='*60}")
        
        if self.errors:
            print(f"\nFailures:")
            for name, err in self.errors:
                print(f"  ✗ {name}: {err}")
        
        return 0 if self.failed == 0 else 1
    
    def _discover(self, path: str) -> list:
        """Discover test files."""
        test_files = []
        if os.path.isfile(path):
            if path.endswith('.urm'):
                test_files.append(path)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for f in sorted(files):
                    if f.startswith('test_') and f.endswith('.urm'):
                        test_files.append(os.path.join(root, f))
        return test_files
    
    def _run_file(self, filepath: str):
        """Run all test functions in a file."""
        print(f"Running: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        
        evaluator = Evaluator()
        
        try:
            lexer = Lexer(source, filepath)
            tokens = lexer.tokenize()
            parser = Parser(tokens, filepath)
            program = parser.parse()
            
            # Execute all declarations (including test functions)
            for decl in program.declarations:
                evaluator._exec_decl(decl, evaluator.global_env)
            for stmt in program.statements:
                evaluator._exec_stmt(stmt, evaluator.global_env)
            
            # Run test functions
            for decl in program.declarations:
                if isinstance(decl, FuncDecl) and decl.name.startswith('test_'):
                    self._run_test(decl.name, evaluator)
            
        except Exception as e:
            print(f"  ✗ Failed to parse: {e}")
            self.failed += 1
            self.errors.append((filepath, str(e)))
    
    def _run_test(self, name: str, evaluator: Evaluator):
        """Run a single test function."""
        try:
            fn = evaluator.global_env.get(name)
            evaluator._call_function(fn, [])
            self.passed += 1
            print(f"  ✓ {name}")
        except Exception as e:
            self.failed += 1
            self.errors.append((name, str(e)))
            print(f"  ✗ {name}: {e}")
