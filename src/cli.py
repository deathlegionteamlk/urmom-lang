#!/usr/bin/env python3
"""
Urmom Lang CLI - Main entry point.
The 'urm' command-line tool.

Usage:
    urm run <file.urm>         Run a Urmom Lang program
   urm eval <expression>       Evaluate an expression
    urm repl                   Start interactive REPL
    urm check <file.urm>       Check syntax without running
    urm fmt <file.urm>         Format source code
    urm init <project-name>    Initialize a new project
    urm version                Show version info
    urm help                   Show help
"""

import sys
import os
import argparse
import readline  # For REPL history

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import __version__, __author__, __language__
from src.lexer import Lexer
from src.parser import Parser
from src.evaluator import Evaluator, ThrowSignal, ReturnValue, URM_NONE


URM_BANNER = r"""
  _   _                 _       __                          _ 
 | | | | ___  _ __ ___ | |__   / _|_ __ ___   ___ __ _  ___| |
 | | | |/ _ \| '_ ` _ \| '_ \ | |_| '_ ` _ \ / __/ _` |/ _ \ |
 | |_| | (_) | | | | | | |_) ||  _| | | | | | (_| (_| |  __/ |
  \___/ \___/|_| |_| |_|_.__/ |_| |_| |_| |_|\___\__, |\___|_|
                                                   |___/        
  Urmom Lang v{version} by {author}
  Mascot: The Friendly Gopher 🐿️

  Type 'exit()' or press Ctrl+D to quit.
  Type 'help()' for available commands.
""".format(version=__version__, author=__author__)


def run_file(filepath: str) -> int:
    """Run a .urm file and return exit code."""
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.", file=sys.stderr)
        return 1
    if not filepath.endswith('.urm'):
        print(f"Warning: File '{filepath}' doesn't have .urm extension.", file=sys.stderr)

    try:
        with open(filepath, 'r') as f:
            source = f.read()
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    return run_source(source, filepath)


def run_source(source: str, filename: str = "<stdin>") -> int:
    """Parse and evaluate source code."""
    try:
        lexer = Lexer(source, filename)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse()
        evaluator = Evaluator()
        evaluator.run(program)
        return 0
    except ThrowSignal as e:
        from src.evaluator import UrmString
        if isinstance(e.value, UrmString):
            print(f"\nError: {e.value.value}", file=sys.stderr)
        else:
            print(f"\nError: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nRuntime error: {e}", file=sys.stderr)
        return 1


def eval_expression(expr: str) -> int:
    """Evaluate a single expression."""
    # Wrap in println for display
    source = f'println({expr})'
    return run_source(source, "<eval>")


def check_syntax(filepath: str) -> int:
    """Check syntax without executing."""
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.", file=sys.stderr)
        return 1

    try:
        with open(filepath, 'r') as f:
            source = f.read()
        lexer = Lexer(source, filepath)
        tokens = lexer.tokenize()

        # Check for illegal tokens
        from src.lexer.tokens import TokenType
        illegal_tokens = [t for t in tokens if t.type == TokenType.ILLEGAL]
        if illegal_tokens:
            for t in illegal_tokens:
                print(f"  Illegal token at L{t.line}:{t.column} - {t.literal!r}")
            print(f"\nFound {len(illegal_tokens)} error(s).")
            return 1

        parser = Parser(tokens)
        program = parser.parse()
        print(f"✓ Syntax OK - {filepath}")
        # Print stats
        n_decls = len(program.declarations)
        n_stmts = len(program.statements)
        n_imports = len(program.imports)
        print(f"  {n_decls} declaration(s), {n_stmts} statement(s), {n_imports} import(s)")
        return 0
    except Exception as e:
        print(f"✗ Syntax error: {e}", file=sys.stderr)
        return 1


def format_source(filepath: str) -> int:
    """Basic source code formatter."""
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.", file=sys.stderr)
        return 1

    try:
        with open(filepath, 'r') as f:
            source = f.read()

        lexer = Lexer(source, filepath)
        tokens = lexer.tokenize()

        # Simple formatter: normalize whitespace, consistent indentation
        from src.lexer.tokens import TokenType
        output_lines = []
        current_line = []
        indent_level = 0

        for tok in tokens:
            if tok.type == TokenType.EOF:
                break
            if tok.type == TokenType.NEWLINE:
                if current_line:
                    line = " " * (indent_level * 4) + " ".join(current_line)
                    output_lines.append(line)
                    current_line = []
            elif tok.type == TokenType.LBRACE:
                if current_line:
                    line = " " * (indent_level * 4) + " ".join(current_line) + " {"
                    output_lines.append(line)
                    current_line = []
                else:
                    line = " " * (indent_level * 4) + "{"
                    output_lines.append(line)
                indent_level += 1
            elif tok.type == TokenType.RBRACE:
                if current_line:
                    line = " " * (indent_level * 4) + " ".join(current_line)
                    output_lines.append(line)
                    current_line = []
                indent_level = max(0, indent_level - 1)
                line = " " * (indent_level * 4) + "}"
                output_lines.append(line)
            elif tok.type in (TokenType.SEMICOLON, TokenType.COMMA):
                current_line.append(tok.literal)
            else:
                current_line.append(tok.literal)

        formatted = "\n".join(output_lines) + "\n"

        with open(filepath, 'w') as f:
            f.write(formatted)

        print(f"✓ Formatted {filepath}")
        return 0
    except Exception as e:
        print(f"Error formatting: {e}", file=sys.stderr)
        return 1


def init_project(name: str) -> int:
    """Initialize a new Urmom Lang project."""
    project_dir = name
    if os.path.exists(project_dir):
        print(f"Error: Directory '{name}' already exists.", file=sys.stderr)
        return 1

    os.makedirs(project_dir)
    os.makedirs(os.path.join(project_dir, "src"))
    os.makedirs(os.path.join(project_dir, "tests"))

    # Create main.urm
    main_content = f'''// {name} - Urmom Lang Project
// By Death Legion Team

fn main() {{
    println("Hello from {name}!")
    println("Welcome to Urmom Lang!")
}}

main()
'''
    with open(os.path.join(project_dir, "src", "main.urm"), 'w') as f:
        f.write(main_content)

    # Create package.urm
    pkg_content = f'''// Package manifest for {name}
package {name}
version "0.1.0"
author "Your Name"
description "A Urmom Lang project"
'''
    with open(os.path.join(project_dir, "package.urm"), 'w') as f:
        f.write(pkg_content)

    # Create test file
    test_content = f'''// Tests for {name}

fn test_hello() {{
    let greeting = "Hello, World!"
    assert_eq(greeting, "Hello, World!")
    println("test_hello passed")
}}

fn main() {{
    test_hello()
    println("All tests passed!")
}}

main()
'''
    with open(os.path.join(project_dir, "tests", "test_main.urm"), 'w') as f:
        f.write(test_content)

    # Create README
    readme_content = f'''# {name}

A project written in Urmom Lang.

## Getting Started

```bash
urm run src/main.urm
```

## Running Tests

```bash
urm test tests/
```

## Learn More

- [Urmom Lang Documentation](https://urmom-lang.dev)
- [Language Spec](./docs/SPEC.md)
'''
    with open(os.path.join(project_dir, "README.md"), 'w') as f:
        f.write(readme_content)

    print(f"✓ Created project '{name}'")
    print(f"  {project_dir}/src/main.urm")
    print(f"  {project_dir}/tests/test_main.urm")
    print(f"  {project_dir}/package.urm")
    print(f"\nRun it with: urm run {project_dir}/src/main.urm")
    return 0


def start_repl() -> int:
    """Start an interactive REPL."""
    print(URM_BANNER)

    evaluator = Evaluator()
    env = evaluator.global_env

    while True:
        try:
            line = input("urm> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye from Urmom Lang! The Gopher waves farewell. 🐿️")
            break

        line = line.strip()
        if not line:
            continue
        if line in ("exit()", "exit", "quit()", "quit"):
            print("Goodbye! The Gopher waves farewell. 🐿️")
            break
        if line == "help()":
            print_repl_help()
            continue
        if line == "version()":
            print(f"Urmom Lang v{__version__}")
            continue
        if line == "clear()":
            os.system('clear' if os.name != 'nt' else 'cls')
            continue

        # Multi-line input for blocks
        source = line
        brace_count = source.count('{') - source.count('}')
        while brace_count > 0:
            try:
                continuation = input("... ")
                source += "\n" + continuation
                brace_count += continuation.count('{') - continuation.count('}')
            except (EOFError, KeyboardInterrupt):
                print()
                break

        # Try to evaluate
        try:
            lexer = Lexer(source, "<repl>")
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            program = parser.parse()

            # If it's a single expression, print the result
            if (len(program.statements) == 1 and
                hasattr(program.statements[0], 'expression') and
                not isinstance(program.statements[0], (type(None),))):
                from src.nodes import ExpressionStmt
                if isinstance(program.statements[0], ExpressionStmt):
                    result = evaluator._eval_expr(program.statements[0].expression, env)
                    print(f"= {evaluator._value_to_display(result)}")
                    continue

            evaluator.run(program)
        except ThrowSignal as e:
            from src.evaluator import UrmString
            if isinstance(e.value, UrmString):
                print(f"Error: {e.value.value}")
            else:
                print(f"Error: {e}")
        except Exception as e:
            print(f"Error: {e}")


def print_repl_help():
    """Print REPL help."""
    help_text = """
Urmom Lang REPL Commands:
  exit()        Exit the REPL
  help()        Show this help
  version()     Show version
  clear()       Clear the screen

Language Features:
  let x = 10              Variable declaration
  const PI = 3.14         Constant declaration
  fn add(a, b) => a + b   Function definition
  if x > 0 { ... }       Conditional
  for i in range(10) { }  For-in loop
  while x > 0 { ... }    While loop
  spawn fn() { ... }      Spawn concurrent task
  chan(10)                Create channel
  try { ... } catch e { } Error handling

Built-in Functions:
  println, print, len, range, type_of
  to_string, to_int, to_float
  abs, min, max, floor, ceil, sqrt, pow
  rand, rand_int, sleep, time_now
  assert, assert_eq, panic
  map, filter, reduce, sort, reverse
  join, split, trim, upper, lower, replace
  parse_json, to_json

Standard Library Modules:
  std.io     - Input/output
  std.fs     - File system
  std.net    - Networking
  std.math   - Math functions
  std.time   - Time functions
  std.data   - Data manipulation
  std.rand   - Random number generation
  std.regex  - Regular expressions
  std.concurrency - Concurrency primitives
"""
    print(help_text)


def main():
    parser = argparse.ArgumentParser(
        prog='urm',
        description=f'{__language__} - A modern, simple, concurrent programming language by {__author__}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''Examples:
  urm run hello.urm          Run a program
  urm repl                   Start interactive mode
  urm eval "2 + 3"          Evaluate an expression
  urm init my_project        Create a new project
  urm check hello.urm        Check syntax

Mascot: The Friendly Gopher
'''
    )

    parser.add_argument('--version', action='version', version=f'Urmom Lang v{__version__}')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # run
    run_parser = subparsers.add_parser('run', help='Run a Urmom Lang program')
    run_parser.add_argument('file', help='Path to .urm file')

    # eval
    eval_parser = subparsers.add_parser('eval', help='Evaluate an expression')
    eval_parser.add_argument('expression', help='Expression to evaluate')

    # repl
    subparsers.add_parser('repl', help='Start interactive REPL')

    # check
    check_parser = subparsers.add_parser('check', help='Check syntax')
    check_parser.add_argument('file', help='Path to .urm file')

    # fmt
    fmt_parser = subparsers.add_parser('fmt', help='Format source code')
    fmt_parser.add_argument('file', help='Path to .urm file')

    # init
    init_parser = subparsers.add_parser('init', help='Initialize a new project')
    init_parser.add_argument('name', help='Project name')

    # test
    test_parser = subparsers.add_parser('test', help='Run tests')
    test_parser.add_argument('path', help='Test file or directory', nargs='?', default='tests/')

    # build
    build_parser = subparsers.add_parser('build', help='Build project')
    build_parser.add_argument('path', help='Source directory', nargs='?', default='src/')

    args = parser.parse_args()

    if args.command == 'run':
        sys.exit(run_file(args.file))
    elif args.command == 'eval':
        sys.exit(eval_expression(args.expression))
    elif args.command == 'repl':
        sys.exit(start_repl())
    elif args.command == 'check':
        sys.exit(check_syntax(args.file))
    elif args.command == 'fmt':
        sys.exit(format_source(args.file))
    elif args.command == 'init':
        sys.exit(init_project(args.name))
    elif args.command == 'test':
        from tools.test_runner import run_tests
        sys.exit(run_tests(args.path))
    elif args.command == 'build':
        print("Build command - compiles to bytecode (coming in v0.2.0)")
        sys.exit(0)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == '__main__':
    main()
