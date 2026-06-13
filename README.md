# Urmom Lang

<div align="center">

**A standalone programming language with first-class concurrency, pattern matching, pipe operators, and a comprehensive standard library.**

*By Death Legion Team*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.2.0-green.svg)](https://github.com/death-legion/urmom-lang)

</div>

---

## What is Urmom Lang?

Urmom Lang is a **standalone programming language** — it has its own syntax, own object model, own type system, own concurrency primitives, and own standard library. It is NOT a wrapper around Python or any other language. The language features:

- **Simple & Modern Syntax** — Clean, readable, and easy to learn
- **Immutable by Default** — `let` for immutable, `let mut` for mutable
- **First-Class Concurrency** — `spawn`, `chan` (channels), futures, mutexes
- **Pattern Matching** — Powerful `match` expressions with destructuring
- **Pipe Operator** — `|>` for elegant function chaining
- **Null-Safe Access** — `?.` operator for safe navigation
- **Struct/Enum/Trait/Impl** — Full type system with traits and implementations
- **Comprehensive Standard Library** — 15+ stdlib modules
- **Full Tooling** — Compiler/interpreter, package manager, test framework, REPL

## Quick Start

```bash
# Install
pip install urmom-lang

# Run a file
urm run hello.urm

# Start REPL
urm repl

# Evaluate expression
urm eval 'println("Hello, World!")'

# Run tests
urm test tests/

# Check syntax
urm check myfile.urm
```

## Hello World

```urm
println("Hello, World from Urmom Lang!")
```

## Language Tour

### Variables

```urm
let x = 10              // Immutable (default)
let mut y = 20          // Mutable
const VERSION = "0.2.0" // Constant
```

### Functions

```urm
fn greet(name) {
    println("Hello, " + name + "!")
}

// Lambda expressions
let double = fn(x) => x * 2
let add = fn(a, b) => a + b

// Closures
fn make_counter(start) {
    let mut count = start
    fn() {
        count = count + 1
        count
    }
}
```

### Control Flow

```urm
if score >= 90 {
    println("A")
} elif score >= 80 {
    println("B")
} else {
    println("C")
}

// For-in loops
for item in [10, 20, 30] {
    println(item)
}

// While loops
let mut i = 0
while i < 10 {
    i = i + 1
}

// Infinite loops
loop {
    if done { break }
}
```

### Pattern Matching

```urm
match value {
    0 => println("zero")
    1 => println("one")
    42 => println("the answer!")
    _ => println("something else")
}
```

### Structs

```urm
struct Point {
    x: int
    y: int
    
    fn magnitude(self) {
        sqrt(self.x * self.x + self.y * self.y)
    }
}

let p = Point(3, 4)
println(p.magnitude())  // 5.0
```

### Enums

```urm
enum Color {
    Red
    Green
    Blue
}

let c = Color::Red
match c {
    Color::Red => println("Red!")
    _ => println("Other!")
}
```

### Concurrency

```urm
// Spawn a task
let task = spawn fn() {
    42
}
println(task.get_value())  // 42

// Channels
let ch = chan(10)
spawn fn() {
    for i in range(5) {
        ch.send(i)
    }
    ch.close()
}

// Parallel processing
let mut futures = []
for n in [1, 2, 3, 4, 5] {
    let num = n
    let f = spawn fn() { num * num }
    push(futures, f)
}
```

### Pipe Operator

```urm
let result = [1, 2, 3, 4, 5]
    |> fn(arr) => map(fn(x) => x * 2, arr)
    |> fn(arr) => filter(fn(x) => x > 5, arr)
```

### Error Handling

```urm
try {
    let result = risky_operation()
} catch as err {
    println("Error: " + str(err))
} finally {
    println("Cleanup")
}

// Assertions
assert 1 + 1 == 2, "Math works"
```

### String Interpolation

```urm
let name = "World"
println("Hello, ${name}!")
```

## Standard Library

| Module | Description |
|--------|-------------|
| `std.io` | Input/output operations |
| `std.fs` | File system operations |
| `std.net` | HTTP client, DNS, URL parsing |
| `std.math` | Mathematical functions (trig, log, etc.) |
| `std.time` | Time formatting, timestamps, sleep |
| `std.data` | JSON, CSV, sorting, grouping |
| `std.rand` | Random number generation |
| `std.regex` | Regular expressions |
| `std.concurrency` | Spawn, channels, mutexes |
| `std.crypto` | MD5, SHA256, SHA512 hashing |
| `std.encoding` | Base64, hex, URL encoding |
| `std.os` | Environment variables, platform info |
| `std.process` | Process execution |
| `std.path` | Path manipulation |
| `std.uuid` | UUID generation |
| `std.collections` | Permutations, combinations, counters |

### Built-in Functions

**I/O:** `print`, `println`, `read_line`, `read_file`, `write_file`

**Types:** `int`, `float`, `str`, `bool`, `type_of`

**Collections:** `len`, `range`, `map`, `filter`, `reduce`, `sort`, `reverse`, `flatten`, `unique`, `min`, `max`, `sum`, `any`, `all`, `contains`, `find`, `chunk`, `join`, `split`, `push`, `pop`

**String:** `trim`, `upper`, `lower`, `replace`, `starts_with`, `ends_with`, `repeat`, `format`, `pad_left`, `pad_right`

**Math:** `abs`, `floor`, `ceil`, `round`, `sqrt`, `pow`, `log`, `sin`, `cos`, `tan`

**Time:** `time_now`, `time_format`, `sleep`

**Random:** `random`, `random_int`, `random_choice`, `random_shuffle`

**Concurrency:** `spawn`, `chan`, `select`, `mutex`

**Crypto:** `md5`, `sha256`, `sha512`

**Encoding:** `base64_encode`, `base64_decode`, `hex_encode`, `hex_decode`, `url_encode`, `url_decode`

**JSON:** `json_parse`, `json_stringify`

**Regex:** `regex`, `regex_match`, `regex_search`, `regex_replace`, `regex_split`, `regex_find_all`

**UUID:** `uuid`, `uuid_v4`

**OS:** `env_get`, `env_set`, `cwd`, `args`, `exec`, `exit`

**FS:** `file_exists`, `is_dir`, `is_file`, `list_dir`, `make_dir`, `remove`, `rename`, `copy`, `path_join`

**Iterator:** `iterate`, `take`, `drop`, `cycle`, `chain`, `permutations`, `combinations`, `group_by`, `partition`

**Utility:** `memoize`, `deep_copy`, `deep_eq`

## CLI Commands

```bash
urm run <file>       # Run an Urmom Lang file
urm eval <code>      # Evaluate an expression
urm repl             # Start interactive REPL
urm check <file>     # Check syntax
urm fmt <file>       # Format source code
urm init <name>      # Initialize a new project
urm test <dir>       # Run tests
```

## Package Manager

```bash
urm-pkg init <name>     # Initialize a package
urm-pkg install <pkg>   # Install a package
urm-pkg uninstall <pkg> # Remove a package
urm-pkg list            # List installed packages
urm-pkg search <query>  # Search packages
urm-pkg publish         # Publish a package
urm-pkg update [pkg]    # Update packages
```

## Project Structure

```
urmom-lang/
├── src/
│   ├── vm/           # Virtual Machine (opcodes, object model)
│   ├── lexer/        # Tokenizer
│   ├── parser/       # Recursive descent parser
│   ├── ast/          # Abstract Syntax Tree nodes
│   ├── runtime/      # Evaluator/VM runtime
│   ├── stdlib/       # Standard library modules
│   ├── tools/        # Package manager, test runner
│   └── cli.py        # Command-line interface
├── examples/         # Example programs
├── tests/            # Test suite
├── docs/             # Documentation
└── pyproject.toml    # Package configuration
```

## License

MIT License — Copyright (c) 2024 Death Legion Team
