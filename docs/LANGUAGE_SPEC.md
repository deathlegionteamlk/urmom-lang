# Urmom Lang Language Specification v0.1.0

**By Death Legion Team**

This document provides a comprehensive specification for the Urmom Lang programming language, covering syntax, semantics, type system, concurrency model, and standard library.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Lexical Structure](#2-lexical-structure)
3. [Types](#3-types)
4. [Variables and Constants](#4-variables-and-constants)
5. [Expressions](#5-expressions)
6. [Statements](#6-statements)
7. [Functions](#7-functions)
8. [Structs and Traits](#8-structs-and-traits)
9. [Enums](#9-enums)
10. [Error Handling](#10-error-handling)
11. [Concurrency](#11-concurrency)
12. [Module System](#12-module-system)
13. [Standard Library](#13-standard-library)
14. [Grammar Reference](#14-grammar-reference)

---

## 1. Overview

Urmom Lang is a statically-typed, concurrent programming language with a focus on simplicity and developer productivity. The language is designed around the following core principles:

- **Readability**: Code should read like natural language wherever possible.
- **Safety**: Immutable by default, explicit mutation, comprehensive error handling.
- **Concurrency**: First-class support for lightweight concurrent tasks and message-passing.
- **Pragmatism**: The language should solve real-world problems with minimal ceremony.

### Hello World

```urm
fn main() {
    println("Hello, World!")
}
main()
```

---

## 2. Lexical Structure

### 2.1 Comments

```urm
// Single-line comment

/* Multi-line
   comment */
```

### 2.2 Keywords

```
let const fn return if elif else for in while break continue
match struct impl trait enum import from as pub mut spawn chan
try catch finally throw type none true false self super where
async await defer
```

### 2.3 Operators

| Category | Operators |
|----------|-----------|
| Arithmetic | `+ - * / % **` |
| Comparison | `== != < > <= >=` |
| Logical | `&& \|\| !` |
| Bitwise | `& \| ^ ~ << >>` |
| Assignment | `= += -= *= /=` |
| Arrow | `-> =>` |

### 2.4 Literals

```urm
42              // Integer
3.14            // Float
0xFF            // Hex
0b1010          // Binary
1_000_000       // With separators
"hello"         // String
"escape\n\t"    // String with escapes
true            // Boolean
false           // Boolean
none            // None
[1, 2, 3]       // Array
{"a": 1}        // Dictionary
(1, 2, 3)       // Tuple
```

### 2.5 Identifiers

Identifiers start with a letter or underscore, followed by letters, digits, or underscores:

```
x, myVar, _private, CamelCase, snake_case
```

---

## 3. Types

### 3.1 Primitive Types

| Type | Description | Examples |
|------|-------------|----------|
| `int` | 64-bit signed integer | `42`, `-7`, `0xFF` |
| `float` | 64-bit floating point | `3.14`, `-0.5` |
| `string` | UTF-8 string | `"hello"` |
| `bool` | Boolean | `true`, `false` |
| `none` | Absence of value | `none` |

### 3.2 Composite Types

- **Array**: `[]int`, `[]string` — ordered, growable sequences
- **Dict**: `dict[string, int]` — key-value maps with string keys
- **Tuple**: `(int, string, bool)` — fixed-size heterogeneous sequences
- **Struct**: User-defined named types with fields
- **Enum**: Sum types with named variants
- **Chan**: Typed channels for concurrent communication
- **Function**: First-class callable values

### 3.3 Type Annotations

```urm
let x: int = 42
let name: string = "Urmom"
let scores: []int = [90, 85, 92]
let data: dict = {"key": "value"}
```

Type annotations are optional — Urmom Lang infers types where possible.

---

## 4. Variables and Constants

### 4.1 Variable Declaration

```urm
// Immutable (default)
let name = "Urmom Lang"

// Mutable
let mut counter = 0
counter += 1

// With type annotation
let x: int = 42
```

### 4.2 Constant Declaration

```urm
const PI = 3.14159265
const MAX_SIZE = 1024
```

Constants cannot be reassigned. They must be initialized at declaration.

---

## 5. Expressions

### 5.1 Arithmetic

```urm
1 + 2       // Addition
10 - 3      // Subtraction
4 * 5       // Multiplication
15 / 3      // Division
10 % 3      // Modulo
2 ** 8      // Exponentiation (256)
```

### 5.2 String Concatenation

```urm
"Hello" + " " + "World"  // "Hello World"
```

### 5.3 Comparison

```urm
a == b      // Equal
a != b      // Not equal
a < b       // Less than
a > b       // Greater than
a <= b      // Less than or equal
a >= b      // Greater than or equal
```

### 5.4 Logical

```urm
a && b      // Logical AND
a || b      // Logical OR
!a          // Logical NOT
```

### 5.5 Bitwise

```urm
a & b       // Bitwise AND
a | b       // Bitwise OR
a ^ b       // Bitwise XOR
~a          // Bitwise NOT
a << n      // Left shift
a >> n      // Right shift
```

### 5.6 Indexing and Slicing

```urm
arr[0]          // Index access
arr[1:4]        // Slice
arr[:3]         // Slice from start
arr[2:]         // Slice to end
dict["key"]     // Dict access
```

### 5.7 Member Access

```urm
obj.field       // Field access
obj.method()    // Method call
```

---

## 6. Statements

### 6.1 Expression Statements

Any expression can be used as a statement:

```urm
println("hello")
x + 1  // Result is discarded
```

### 6.2 Assignment

```urm
x = 42
arr[0] = 10
obj.field = "new"
x += 5      // Compound assignment
x -= 3
x *= 2
x /= 4
```

### 6.3 Control Flow

#### If/Elif/Else

```urm
if condition {
    // ...
} elif other_condition {
    // ...
} else {
    // ...
}
```

#### For-In

```urm
for item in collection {
    println(item)
}

for i in range(0, 10) {
    println(i)
}
```

#### While

```urm
while condition {
    // ...
}
```

#### Match

```urm
match value {
    pattern1 => { handle1() }
    pattern2 => { handle2() }
    _ => { default() }
}
```

#### Break and Continue

```urm
for item in items {
    if item == "skip" { continue }
    if item == "stop" { break }
    process(item)
}
```

### 6.4 Return

```urm
fn add(a, b) {
    return a + b  // Explicit return
}

fn double(x) {
    x * 2  // Implicit return (last expression)
}
```

---

## 7. Functions

### 7.1 Function Declaration

```urm
fn name(param1, param2) {
    // body
}
```

### 7.2 Parameters

```urm
// Default parameters
fn power(base, exp = 2) {
    pow(base, exp)
}

// Variadic parameters
fn sum_all(...numbers) {
    reduce(fn(a, b) => a + b, numbers, 0)
}

// Typed parameters
fn process(data: string, count: int) {
    // ...
}
```

### 7.3 Lambda Functions

```urm
// Expression body
let double = fn(x) => x * 2

// Block body
let compute = fn(x) {
    let y = x * 2
    y + 1
}
```

### 7.4 Closures

Functions capture their enclosing scope:

```urm
fn make_counter() {
    let mut count = 0
    fn() {
        count += 1
        count
    }
}

let counter = make_counter()
counter()  // 1
counter()  // 2
counter()  // 3
```

### 7.5 Higher-Order Functions

```urm
let numbers = [1, 2, 3, 4, 5]

let doubled = map(fn(x) => x * 2, numbers)
let evens = filter(fn(x) => x % 2 == 0, numbers)
let sum = reduce(fn(acc, x) => acc + x, numbers, 0)
```

---

## 8. Structs and Traits

### 8.1 Struct Declaration

```urm
struct Point {
    x: int
    y: int
}

let p = Point(3, 4)
println(p.x)  // 3
println(p.y)  // 4
```

### 8.2 Struct Methods (impl)

```urm
impl Point {
    fn distance(self) {
        sqrt(pow(self.x, 2) + pow(self.y, 2))
    }

    fn translate(self, dx, dy) {
        Point(self.x + dx, self.y + dy)
    }
}
```

### 8.3 Traits

```urm
trait Drawable {
    fn draw(self)
    fn area(self)
}

impl Drawable for Circle {
    fn draw(self) {
        println("Drawing circle at (" + to_string(self.x) + ", " + to_string(self.y) + ")")
    }
    fn area(self) {
        3.14159265 * self.radius * self.radius
    }
}
```

### 8.4 Visibility

```urm
struct User {
    pub name: string      // Public field
    email: string         // Private field
    pub age: int          // Public field
}

pub fn public_api() {     // Public function
    // ...
}

fn internal_helper() {     // Private function
    // ...
}
```

---

## 9. Enums

### 9.1 Basic Enums

```urm
enum Color {
    Red
    Green
    Blue
}

enum Status {
    Ok
    Error
    Loading
}
```

### 9.2 Enums with Values

```urm
enum Result {
    Ok(value)
    Error(message)
}

enum Shape {
    Circle(radius)
    Rectangle(width, height)
    Triangle(a, b, c)
}
```

---

## 10. Error Handling

### 10.1 Try-Catch-Finally

```urm
try {
    let result = risky_operation()
    process(result)
} catch e {
    println("Error: " + to_string(e))
} finally {
    cleanup()
}
```

### 10.2 Throw

```urm
fn validate_age(age) {
    if age < 0 {
        throw "Age cannot be negative"
    }
    if age > 150 {
        throw "Age seems unrealistic"
    }
}
```

### 10.3 Assertions

```urm
assert(condition, "Error message")
assert_eq(expected, actual)
panic("Unrecoverable error")
```

### 10.4 Defer

```urm
fn process_file(path) {
    let file = open_file(path)
    defer file.close()  // Runs when function exits
    // ... process file ...
}
```

---

## 11. Concurrency

### 11.1 Spawn

The `spawn` keyword creates a lightweight concurrent task:

```urm
let task = spawn fn() {
    heavy_computation()
}

// Do other work...

let result = task.get_value()  // Await the result
```

### 11.2 Channels

Channels provide typed, thread-safe communication between concurrent tasks:

```urm
// Create a channel with optional buffer capacity
let ch = chan(10)

// Spawn a producer
spawn fn() {
    for i in range(1, 11) {
        ch.send(i)
    }
}

// Consume from channel
let value = ch.receive()
```

### 11.3 Async/Await

```urm
async fn fetch_data(url) {
    let response = await http_get(url)
    parse_json(response)
}
```

### 11.4 Concurrency Patterns

**Fan-Out/Fan-In:**
```urm
let ch = chan(100)

// Fan out: multiple workers
for i in range(1, 5) {
    spawn fn() {
        ch.send(process_work(i))
    }
}

// Fan in: collect results
let mut results = []
for i in range(1, 5) {
    append(results, ch.receive())
}
```

**Pipeline:**
```urm
let input = chan(10)
let processed = chan(10)
let output = chan(10)

// Stage 1: Read
spawn fn() {
    for item in read_items() {
        input.send(item)
    }
}

// Stage 2: Process
spawn fn() {
    let item = input.receive()
    processed.send(transform(item))
}

// Stage 3: Write
spawn fn() {
    let item = processed.receive()
    write_output(item)
}
```

---

## 12. Module System

### 12.1 Import

```urm
// Import entire module
import std.math

// Import specific items
from std.fs import read_file, write_file

// Import with alias
import std.net as network

// From-import with alias
from std.io import println as log
```

### 12.2 Module Files

Each `.urm` file is a module. Public items (marked with `pub`) are exported:

```urm
// utils.urm
pub fn helper() {
    // Exported
}

fn internal() {
    // Not exported
}
```

```urm
// main.urm
from utils import helper

helper()  // Works
// internal()  // Error: not exported
```

---

## 13. Standard Library

### 13.1 std.io — Input/Output

| Function | Signature | Description |
|----------|-----------|-------------|
| `print` | `print(...args)` | Print without newline |
| `println` | `println(...args)` | Print with newline |
| `printf` | `printf(fmt, ...args)` | Formatted print |
| `read_line` | `read_line()` | Read line from stdin |

### 13.2 std.fs — File System

| Function | Signature | Description |
|----------|-----------|-------------|
| `read_file` | `read_file(path)` | Read file contents |
| `write_file` | `write_file(path, content)` | Write to file |
| `exists` | `exists(path)` | Check if path exists |
| `mkdir` | `mkdir(path)` | Create directory |
| `list_dir` | `list_dir(path)` | List directory contents |
| `remove` | `remove(path)` | Delete file/directory |
| `is_dir` | `is_dir(path)` | Check if directory |
| `is_file` | `is_file(path)` | Check if file |
| `size` | `size(path)` | Get file size |
| `copy` | `copy(src, dst)` | Copy file |
| `rename` | `rename(old, new)` | Rename/move file |
| `cwd` | `cwd()` | Current working directory |
| `path_join` | `path_join(...parts)` | Join path components |

### 13.3 std.net — Networking

| Function | Signature | Description |
|----------|-----------|-------------|
| `http_get` | `http_get(url)` | HTTP GET request |
| `http_post` | `http_post(url, body)` | HTTP POST request |
| `resolve_host` | `resolve_host(hostname)` | DNS resolution |

### 13.4 std.math — Mathematics

| Function/Constant | Description |
|-------------------|-------------|
| `pi`, `e`, `inf` | Mathematical constants |
| `sin`, `cos`, `tan` | Trigonometric functions |
| `log`, `log2`, `log10` | Logarithmic functions |
| `abs`, `floor`, `ceil`, `round` | Rounding functions |
| `sqrt`, `pow` | Power functions |
| `min`, `max` | Comparison functions |

### 13.5 std.time — Time

| Function | Signature | Description |
|----------|-----------|-------------|
| `now` | `now()` | Current Unix timestamp |
| `format` | `format(fmt, timestamp?)` | Format time |
| `sleep` | `sleep(seconds)` | Sleep for duration |
| `parse` | `parse(fmt, string)` | Parse time string |

### 13.6 std.data — Data Manipulation

| Function | Signature | Description |
|----------|-----------|-------------|
| `parse_json` | `parse_json(string)` | Parse JSON string |
| `to_json` | `to_json(value)` | Serialize to JSON |
| `parse_csv` | `parse_csv(string)` | Parse CSV string |
| `to_csv` | `to_csv(array)` | Serialize to CSV |
| `encode_base64` | `encode_base64(string)` | Encode to Base64 |
| `decode_base64` | `decode_base64(string)` | Decode from Base64 |

### 13.7 std.rand — Random

| Function | Signature | Description |
|----------|-----------|-------------|
| `int` | `int(min, max)` | Random integer |
| `float` | `float(max?)` | Random float |
| `choice` | `choice(array)` | Random element |
| `shuffle` | `shuffle(array)` | Shuffle in place |
| `seed` | `seed(value)` | Set random seed |

### 13.8 std.regex — Regular Expressions

| Function | Signature | Description |
|----------|-----------|-------------|
| `match` | `match(pattern, text)` | Test regex match |
| `find_all` | `find_all(pattern, text)` | Find all matches |
| `replace` | `replace(pattern, replacement, text)` | Regex replace |

### 13.9 std.concurrency — Concurrency

| Function | Signature | Description |
|----------|-----------|-------------|
| `spawn` | `spawn(fn, ...args)` | Run function concurrently |
| `chan` | `chan(capacity?)` | Create a channel |

---

## 14. Grammar Reference

```
program        → declaration* EOF
declaration    → funcDecl | structDecl | traitDecl | enumDecl | implDecl | importDecl | statement

funcDecl       → "pub"? "fn" IDENT "(" params? ")" ("->" type)? block
structDecl     → "pub"? "struct" IDENT "{" field* "}"
traitDecl      → "pub"? "trait" IDENT "{" funcDecl* "}"
enumDecl       → "pub"? "enum" IDENT "{" variant ("," variant)* "}"
implDecl       → "impl" IDENT ("for" IDENT)? "{" funcDecl* "}"
importDecl     → "import" modulePath ("as" IDENT)?
               | "from" modulePath "import" importItems

params         → param ("," param)*
param          → "..."? IDENT (":" type)? ("=" expr)?

block          → "{" statement* "}"
statement      → letStmt | constStmt | ifStmt | whileStmt | forStmt
               | matchStmt | tryStmt | returnStmt | throwStmt | deferStmt
               | assignStmt | exprStmt

letStmt        → "let" "mut"? IDENT (":" type)? ("=" expr)?
constStmt      → "const" IDENT (":" type)? "=" expr
ifStmt         → "if" expr block ("elif" expr block)* ("else" block)?
whileStmt      → "while" expr block
forStmt        → "for" IDENT "in" expr block
               | "for" stmt? ";" expr? ";" expr? block
matchStmt      → "match" expr "{" matchArm* "}"
matchArm       → expr ("where" expr)? "=>" block
tryStmt        → "try" block ("catch" IDENT? block)? ("finally" block)?

expr           → orExpr
orExpr         → andExpr ("||" andExpr)*
andExpr        → equalityExpr ("&&" equalityExpr)*
equalityExpr   → comparisonExpr (("==" | "!=") comparisonExpr)*
comparisonExpr → bitwiseExpr (("<" | ">" | "<=" | ">=") bitwiseExpr)*
bitwiseExpr    → rangeExpr (("&" | "|" | "^" | "<<" | ">>") rangeExpr)*
rangeExpr      → addExpr
addExpr        → mulExpr (("+" | "-") mulExpr)*
mulExpr        → powerExpr (("*" | "/" | "%") powerExpr)*
powerExpr      → unaryExpr ("**" unaryExpr)?
unaryExpr      → ("!" | "-" | "~" | "spawn" | "await" | "chan") unaryExpr | postfixExpr
postfixExpr    → primary ("." IDENT ("(" args ")")? | "(" args ")" | "[" expr "]")*
primary        → INT | FLOAT | STRING | "true" | "false" | "none"
               | IDENT | "(" expr ("," expr)* ")" | "[" expr ("," expr)* "]"
               | "{" expr ":" expr ("," expr ":" expr)* "}" | lambda

lambda         → "fn" "(" params ")" "=>" (block | expr)
```

---

*Urmom Lang Language Specification v0.1.0 — Death Legion Team*
