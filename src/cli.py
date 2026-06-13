"""
Urmom Lang CLI
==============
Command-line interface for the Urmom Lang programming language.
Provides: run, eval, repl, check, fmt, init, test commands.
"""

import sys
import os
import argparse

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lexer import Lexer
from src.parser import Parser
from src.runtime import Evaluator, UrmRuntimeError
from src.vm.objects import URM_NONE


VERSION = "0.2.0"
AUTHOR = "Death Legion Team"


def run_file(filepath: str):
    """Run an Urmom Lang source file."""
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1
    
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    evaluator = Evaluator()
    try:
        evaluator.run(source, filepath)
        return 0
    except UrmRuntimeError as e:
        print(f"\n{e.error_type}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


def eval_source(source: str):
    """Evaluate a string of Urmom Lang code."""
    evaluator = Evaluator()
    try:
        result = evaluator.run(source, "<eval>")
        return result
    except UrmRuntimeError as e:
        print(f"{e.error_type}: {e.message}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


def run_repl():
    """Start the interactive REPL."""
    evaluator = Evaluator()
    
    banner = f"""
╔══════════════════════════════════════════════════════════╗
║   Urmom Lang v{VERSION} - by {AUTHOR}          ║
║   A standalone programming language with first-class     ║
║   concurrency, pattern matching, pipe operators, and     ║
║   a comprehensive standard library.                     ║
║                                                          ║
║   Type 'exit' to quit, 'help' for help.                 ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)
    
    multiline = False
    lines = []
    prompt = "urm> "
    
    while True:
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        
        line = line.strip()
        
        if line == "exit" or line == "quit":
            print("Goodbye!")
            break
        
        if line == "help":
            print("""
Urmom Lang REPL Commands:
  exit/quit  - Exit the REPL
  help       - Show this help
  vars       - Show defined variables
  history    - Show command history

Language Features:
  Variables:    let x = 10, let mut y = 20
  Functions:    fn add(a, b) => a + b
  Structs:      struct Point { x: int, y: int }
  Enums:        enum Color { Red, Green, Blue }
  Concurrency:  spawn fn() { ... }, chan(10)
  Pattern match: match x { when 1 => ..., _ => ... }
  Pipe:         [1,2,3] |> map(fn(x) => x * 2)
  Ranges:       0..10, 0..<10
  Null-safe:    obj?.method()
""")
            continue
        
        if line == "vars":
            for name, val in evaluator.global_env.variables.items():
                print(f"  {name} = {_repr_val(val)}")
            continue
        
        if not line:
            continue
        
        # Handle multi-line
        if line.endswith('{') or line.startswith('fn') or line.startswith('struct') or \
           line.startswith('enum') or line.startswith('impl') or line.startswith('trait') or \
           line.startswith('if') or line.startswith('while') or line.startswith('for') or \
           line.startswith('match') or line.startswith('loop'):
            multiline = True
            lines.append(line)
            prompt = "... "
            continue
        
        if multiline:
            lines.append(line)
            open_braces = sum(l.count('{') for l in lines) - sum(l.count('}') for l in lines)
            if open_braces <= 0:
                multiline = False
                prompt = "urm> "
                source = '\n'.join(lines)
                lines = []
            else:
                continue
        else:
            source = line
        
        try:
            result = evaluator.run(source, "<repl>")
            if result is not None and not isinstance(result, type(URM_NONE)):
                from src.vm.objects import _repr
                print(f"  => {_repr(result)}")
        except UrmRuntimeError as e:
            print(f"  {e.error_type}: {e.message}")
        except Exception as e:
            print(f"  Error: {e}")
    
    return 0


def _repr_val(val):
    from src.vm.objects import _repr
    if isinstance(val, type(URM_NONE)):
        return "none"
    return _repr(val)


def check_file(filepath: str):
    """Check syntax without executing."""
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1
    
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    try:
        lexer = Lexer(source, filepath)
        tokens = lexer.tokenize()
        parser = Parser(tokens, filepath)
        program = parser.parse()
        print(f"✓ {filepath}: Syntax OK ({len(program.declarations)} declarations, {len(program.statements)} statements)")
        return 0
    except Exception as e:
        print(f"✗ {filepath}: {e}", file=sys.stderr)
        return 1


def format_file(filepath: str):
    """Format an Urmom Lang source file (basic formatting)."""
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1
    
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    # Basic formatting: normalize whitespace
    lines = source.split('\n')
    formatted = []
    indent = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted.append('')
            continue
        
        # Decrease indent for closing braces
        if stripped.startswith('}'):
            indent = max(0, indent - 1)
        
        formatted.append('    ' * indent + stripped)
        
        # Increase indent after opening braces
        if stripped.endswith('{'):
            indent += 1
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(formatted))
    
    print(f"Formatted: {filepath}")
    return 0


def init_project(name: str):
    """Initialize a new Urmom Lang project."""
    os.makedirs(name, exist_ok=True)
    os.makedirs(os.path.join(name, 'src'), exist_ok=True)
    os.makedirs(os.path.join(name, 'tests'), exist_ok=True)
    os.makedirs(os.path.join(name, 'examples'), exist_ok=True)
    
    # Main file
    with open(os.path.join(name, 'src', 'main.urm'), 'w') as f:
        f.write(f'''// {name} - Urmom Lang Project
// Created with Urmom Lang v{VERSION}

fn main() {{
    println("Hello from {name}!")
}}
''')
    
    # Project config
    with open(os.path.join(name, 'urm.toml'), 'w') as f:
        f.write(f'''[package]
name = "{name}"
version = "0.1.0"
authors = ["{AUTHOR}"]
edition = "2024"

[dependencies]
''')
    
    # Test file
    with open(os.path.join(name, 'tests', 'test_main.urm'), 'w') as f:
        f.write('''// Test suite
fn test_hello() {
    assert true, "Basic assertion"
}

fn test_arithmetic() {
    assert 1 + 1 == 2, "Addition works"
}
''')
    
    # README
    with open(os.path.join(name, 'README.md'), 'w') as f:
        f.write(f'''# {name}

A project written in [Urmom Lang](https://github.com/death-legion/urmom-lang) v{VERSION}.

## Usage

```bash
urm run src/main.urm
```

## Testing

```bash
urm-test tests/
```
''')
    
    print(f"Created project: {name}/")
    print(f"  src/main.urm")
    print(f"  tests/test_main.urm")
    print(f"  urm.toml")
    print(f"  README.md")
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='urm',
        description=f'Urmom Lang v{VERSION} - by {AUTHOR}'
    )
    parser.add_argument('--version', action='version', version=f'Urmom Lang v{VERSION}')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # run
    run_parser = subparsers.add_parser('run', help='Run an Urmom Lang file')
    run_parser.add_argument('file', help='Source file to run')
    
    # eval
    eval_parser = subparsers.add_parser('eval', help='Evaluate an expression')
    eval_parser.add_argument('code', help='Code to evaluate')
    
    # repl
    subparsers.add_parser('repl', help='Start interactive REPL')
    
    # check
    check_parser = subparsers.add_parser('check', help='Check syntax')
    check_parser.add_argument('file', help='Source file to check')
    
    # fmt
    fmt_parser = subparsers.add_parser('fmt', help='Format source code')
    fmt_parser.add_argument('file', help='Source file to format')
    
    # init
    init_parser = subparsers.add_parser('init', help='Initialize a new project')
    init_parser.add_argument('name', help='Project name')
    
    # test
    test_parser = subparsers.add_parser('test', help='Run tests')
    test_parser.add_argument('path', nargs='?', default='tests/', help='Test directory')
    
    args = parser.parse_args()
    
    if args.command == 'run':
        return run_file(args.file)
    elif args.command == 'eval':
        result = eval_source(args.code)
        if result is not None:
            from src.vm.objects import _repr
            print(_repr(result))
        return 0
    elif args.command == 'repl':
        return run_repl()
    elif args.command == 'check':
        return check_file(args.file)
    elif args.command == 'fmt':
        return format_file(args.file)
    elif args.command == 'init':
        return init_project(args.name)
    elif args.command == 'test':
        from src.tools.test_runner import TestRunner
        runner = TestRunner()
        return runner.run(args.path)
    else:
        # Default: try to run as file, or start REPL
        if len(sys.argv) > 1 and sys.argv[1].endswith('.urm'):
            return run_file(sys.argv[1])
        return run_repl()


if __name__ == '__main__':
    sys.exit(main() or 0)
