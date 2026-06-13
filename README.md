# Urmom Lang

<p align="center">
  <img src="docs/mascot.png" alt="Urmom Lang Mascot - The Friendly Gopher" width="200"/>
</p>

<p align="center">
  <strong>A modern, simple, concurrent programming language</strong><br>
  <em>By the Death Legion Team</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-teal" alt="Version"/>
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License"/>
  <img src="https://img.shields.io/badge/status-alpha-yellow" alt="Status"/>
</p>

---

## What is Urmom Lang?

Urmom Lang is an open-source programming language designed from the ground up to make building software **simple**, **reliable**, and **efficient**. With a modern syntax that's easy to pick up and first-class support for concurrency, Urmom Lang is perfect for building fast backend servers and high-performance network tools.

### Key Features

- **Simple & Modern Syntax** — Clean, minimal syntax inspired by the best parts of Go, Rust, and Python. No unnecessary complexity.
- **First-Class Concurrency** — Built-in `spawn`, `chan`, and `await` primitives make parallel programming feel natural.
- **Comprehensive Standard Library** — Everything you need built-in: networking, file handling, data manipulation, math, regex, and more.
- **Memory Safety** — Immutable by default with explicit `mut` for mutable variables. No null pointer surprises.
- **Error Handling** — `try/catch/finally` with `throw` for robust error management.
- **Rich Type System** — Structs, enums, traits, and type annotations that don't get in your way.
- **Full Tooling** — Compiler, package manager (`urm-pkg`), test runner (`urm-test`), formatter, and REPL included.
- **Friendly Gopher Mascot** — Because programming should be fun! 🐿️

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/death-legion/urmom-lang.git
cd urmom-lang

# Install (requires Python 3.8+)
pip install -e .

# Verify installation
urm version
```

### Hello World

```urm
fn main() {
    println("Hello, World from Urmom Lang!")
}

main()
```

Run it:
```bash
urm run hello.urm
```

### Interactive REPL

```bash
urm repl
```

```
  _   _                 _       __                          _
 | | | | ___  _ __ ___ | |__   / _|_ __ ___   ___ __ _  ___| |
 | | | |/ _ \| '_ ` _ \| '_ \ | |_| '_ ` _ \ / __/ _` |/ _ \ |
 | |_| | (_) | | | | | | |_) ||  _| | | | | | (_| (_| |  __/ |
  \___/ \___/|_| |_| |_|_.__/ |_| |_| |_| |_|\___\__, |\___|_|
                                                   |___/
  Urmom Lang v0.1.0 by Death Legion Team
  Mascot: The Friendly Gopher

urm> println("Hello!")
Hello!
urm> let x = 42
urm> x * 2
= 84
```

---

## Language Tour

### Variables & Constants

```urm
// Immutable by default
let name = "Urmom Lang"
let version = 0.1

// Mutable variables
let mut counter = 0
counter += 1

// Constants (compile-time)
const MAX_SIZE = 1024
const PI = 3.14159265
```

### Functions

```urm
// Basic function
fn add(a, b) {
    a + b  // Implicit return for last expression
}

// With default parameters
fn power(base, exp = 2) {
    pow(base, exp)
}

// Variadic functions
fn sum_all(...numbers) {
    let mut total = 0
    for n in numbers {
        total += n
    }
    total
}

// Lambda / Anonymous functions
let double = fn(x) => x * 2
let square = fn(x) { x * x }
```

### Control Flow

```urm
// If-elif-else
if score >= 90 {
    println("A")
} elif score >= 80 {
    println("B")
} else {
    println("C")
}

// For-in loop
for item in collection {
    println(item)
}

// While loop
while condition {
    // ...
}

// Match statement
match value {
    "option1" => { handle_option1() }
    "option2" => { handle_option2() }
    _ => { handle_default() }
}
```

### Data Structures

```urm
// Arrays
let fruits = ["apple", "banana", "cherry"]
fruits[0]  // "apple"

// Dictionaries
let config = {
    "host": "localhost",
    "port": 8080,
    "debug": true
}
config["host"]  // "localhost"

// Structs
struct Point {
    x: int
    y: int
}

impl Point {
    fn distance(self) {
        sqrt(pow(self.x, 2) + pow(self.y, 2))
    }
}

let p = Point(3, 4)
println(p.distance())  // 5.0

// Enums
enum Result {
    Ok(value)
    Error(message)
}
```

### Concurrency

Urmom Lang's concurrency model is inspired by Go's goroutines and channels:

```urm
// Spawn a concurrent task
let task = spawn fn() {
    // Heavy computation
    let mut sum = 0
    for i in range(1, 1000001) {
        sum += i
    }
    sum
}

// Await the result
let result = task.get_value()
println("Sum: " + to_string(result))

// Channels for communication
let ch = chan(10)  // Buffered channel

// Producer
spawn fn() {
    for i in range(1, 11) {
        ch.send(i)
    }
}

// Consumer
let value = ch.receive()
```

### Error Handling

```urm
try {
    let result = risky_operation()
    println(result)
} catch e {
    println("Error: " + to_string(e))
} finally {
    cleanup()
}

// Throw custom errors
fn validate(age) {
    if age < 0 {
        throw "Age cannot be negative"
    }
    if age > 150 {
        throw "Age seems unrealistic"
    }
}

// Assertions
assert(x > 0, "x must be positive")
assert_eq(expected, actual)
```

---

## Standard Library

| Module | Description |
|--------|-------------|
| `std.io` | Input/output operations (`print`, `println`, `read_line`) |
| `std.fs` | File system (`read_file`, `write_file`, `exists`, `mkdir`, `list_dir`) |
| `std.net` | Networking (`http_get`, `http_post`, `resolve_host`) |
| `std.math` | Math functions (`sin`, `cos`, `sqrt`, `pow`, `log`, constants) |
| `std.time` | Time operations (`now`, `format`, `sleep`, `parse`) |
| `std.data` | Data manipulation (`parse_json`, `to_json`, `parse_csv`, `encode_base64`) |
| `std.rand` | Random generation (`int`, `float`, `choice`, `shuffle`, `seed`) |
| `std.regex` | Regular expressions (`match`, `find_all`, `replace`) |
| `std.concurrency` | Concurrency primitives (`spawn`, `chan`) |

### Using the Standard Library

```urm
// Import specific functions
from std.fs import read_file, write_file
from std.net import http_get

// Or import the whole module
import std.math

let content = read_file("data.txt")
let pi = std.math.pi
```

---

## CLI Tools

### `urm` — Main Command

```bash
urm run <file.urm>       # Run a program
urm eval <expression>     # Evaluate an expression
urm repl                  # Interactive REPL
urm check <file.urm>      # Check syntax
urm fmt <file.urm>        # Format code
urm init <project-name>   # Create new project
urm test [path]           # Run tests
```

### `urm-pkg` — Package Manager

```bash
urm-pkg init              # Initialize package
urm-pkg install <pkg>     # Install a package
urm-pkg uninstall <pkg>   # Remove a package
urm-pkg list              # List installed packages
urm-pkg search <query>    # Search for packages
urm-pkg publish           # Publish to registry
urm-pkg update            # Update all packages
```

### `urm-test` — Test Runner

```bash
urm-test                  # Run all tests
urm-test tests/           # Run tests in directory
urm-test --verbose        # Detailed output
urm-test --filter test_foo  # Run specific test
```

---

## Project Structure

```
my-project/
├── package.urm        # Package manifest
├── urm.lock           # Dependency lock file
├── README.md
├── src/
│   ├── main.urm       # Entry point
│   └── utils.urm      # Module
├── tests/
│   └── test_main.urm  # Tests
└── docs/
    └── SPEC.md        # Language spec
```

---

## Built-in Functions

| Function | Description |
|----------|-------------|
| `println(...)` | Print with newline |
| `print(...)` | Print without newline |
| `len(x)` | Length of string/array/dict |
| `type_of(x)` | Get type name |
| `to_string(x)` | Convert to string |
| `to_int(x)` | Convert to integer |
| `to_float(x)` | Convert to float |
| `range(start, end)` | Generate range |
| `map(fn, arr)` | Map over array |
| `filter(fn, arr)` | Filter array |
| `reduce(fn, arr, init)` | Reduce array |
| `sort(arr)` | Sort array |
| `reverse(arr)` | Reverse array |
| `join(sep, arr)` | Join array to string |
| `split(str, sep)` | Split string |
| `assert(cond, msg)` | Assert condition |
| `assert_eq(a, b)` | Assert equality |
| `panic(msg)` | Unrecoverable error |
| `spawn(fn)` | Run concurrently |
| `chan(cap)` | Create channel |

---

## Language Design Philosophy

1. **Simplicity over complexity** — Features should solve real problems, not create new ones.
2. **Concurrency by default** — Building parallel software shouldn't require a PhD.
3. **Explicit over implicit** — Mutable state should be declared, not assumed.
4. **Batteries included** — The standard library should cover 90% of common needs.
5. **Error handling is not optional** — Robust error handling primitives built into the language.
6. **Fun matters** — Programming should be enjoyable. The Friendly Gopher reminds us not to take ourselves too seriously.

---

## Contributing

We welcome contributions! Here's how:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Write your changes and tests
4. Run the test suite (`urm-test`)
5. Commit with a descriptive message
6. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Team

**Death Legion Team** — Building the future of simple, concurrent programming.

*Mascot: The Friendly Gopher* 🐿️
