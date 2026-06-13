"""
Urmom Lang Bytecode Instruction Set
====================================
Custom instruction set for the Urmom Virtual Machine.
Each instruction has a unique opcode and optional operands.

This is the native bytecode format of Urmom Lang - NOT derived from
any other language's bytecode. Designed from scratch for Urmom Lang's
specific semantics including first-class concurrency, pattern matching,
pipe operators, and null-safe access.
"""

from enum import IntEnum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


class OpCode(IntEnum):
    """Urmom Lang bytecode opcodes - the native instruction set."""
    
    # ═══════════════════════════════════════════
    # Stack Manipulation (0x00-0x0F)
    # ═══════════════════════════════════════════
    NOP = 0x00           # No operation
    POP = 0x01           # Pop top of stack
    DUP = 0x02           # Duplicate top of stack
    SWAP = 0x03          # Swap top two stack elements
    ROT_THREE = 0x04     # Rotate top three stack elements
    OVER = 0x05          # Push copy of second element
    
    # ═══════════════════════════════════════════
    # Load / Store (0x10-0x1F)
    # ═══════════════════════════════════════════
    LOAD_CONST = 0x10    # Load constant from pool
    LOAD_NAME = 0x11     # Load variable by name
    STORE_NAME = 0x12    # Store to variable by name
    LOAD_LOCAL = 0x13    # Load local by slot index
    STORE_LOCAL = 0x14   # Store local by slot index
    LOAD_UPVALUE = 0x15  # Load closure upvalue
    STORE_UPVALUE = 0x16 # Store closure upvalue
    LOAD_GLOBAL = 0x17   # Load global by name
    STORE_GLOBAL = 0x18  # Store global by name
    LOAD_MEMBER = 0x19   # obj.member access
    STORE_MEMBER = 0x1A  # obj.member = value
    LOAD_INDEX = 0x1B    # obj[key] access
    STORE_INDEX = 0x1C   # obj[key] = value
    LOAD_THIS = 0x1D     # Load 'self' reference
    LOAD_SUPER = 0x1E    # Load super reference
    LOAD_ENUM_VARIANT = 0x1F  # Load Enum::Variant
    
    # ═══════════════════════════════════════════
    # Arithmetic (0x20-0x2F)
    # ═══════════════════════════════════════════
    BINARY_ADD = 0x20
    BINARY_SUB = 0x21
    BINARY_MUL = 0x22
    BINARY_DIV = 0x23
    BINARY_MOD = 0x24
    BINARY_POW = 0x25
    BINARY_FLOOR_DIV = 0x26
    UNARY_NEG = 0x27
    UNARY_NOT = 0x28
    UNARY_BIT_NOT = 0x29
    BINARY_AND = 0x2A    # Bitwise AND
    BINARY_OR = 0x2B     # Bitwise OR
    BINARY_XOR = 0x2C    # Bitwise XOR
    BINARY_LSHIFT = 0x2D # Left shift
    BINARY_RSHIFT = 0x2E # Right shift
    INCREMENT = 0x2F     # i++ 
    DECREMENT = 0x2F + 1 # i--
    
    # ═══════════════════════════════════════════
    # Comparison (0x30-0x3F)
    # ═══════════════════════════════════════════
    COMPARE_EQ = 0x30
    COMPARE_NE = 0x31
    COMPARE_LT = 0x32
    COMPARE_LE = 0x33
    COMPARE_GT = 0x34
    COMPARE_GE = 0x35
    IS_INSTANCE = 0x36   # 'is' type check
    SPACESHIP = 0x37     # <=> comparison operator
    MATCH_EQ = 0x38      # Pattern match equality
    MATCH_TYPE = 0x39    # Pattern match type
    
    # ═══════════════════════════════════════════
    # Control Flow (0x40-0x4F)
    # ═══════════════════════════════════════════
    JUMP = 0x40           # Unconditional jump
    JUMP_IF_FALSE = 0x41  # Jump if top is falsy
    JUMP_IF_TRUE = 0x42   # Jump if top is truthy
    JUMP_IF_NULL = 0x43   # Jump if top is null (null-safe)
    LOOP = 0x44           # Backward jump for loops
    FOR_ITER = 0x45       # Get next iterator value or jump
    MATCH_JUMP = 0x46     # Jump table for match
    BREAK = 0x47          # Break out of loop
    CONTINUE = 0x48       # Continue to loop top
    
    # ═══════════════════════════════════════════
    # Function / Call (0x50-0x5F)
    # ═══════════════════════════════════════════
    CALL = 0x50           # Function call
    CALL_METHOD = 0x51    # Method call (obj.method())
    RETURN = 0x52         # Return from function
    YIELD = 0x53          # Yield from generator
    AWAIT = 0x54          # Await async result
    BUILD_TUPLE = 0x55    # Build tuple from stack
    BUILD_LIST = 0x56     # Build list from stack
    BUILD_DICT = 0x57     # Build dict from stack
    BUILD_SET = 0x58      # Build set from stack
    BUILD_RANGE = 0x59    # Build range object
    BUILD_STRING = 0x5A   # String interpolation
    UNPACK_SEQUENCE = 0x5B # Unpack/destructure
    SPREAD = 0x5C         # Spread operator ...
    KW_ARG = 0x5D         # Keyword argument
    DEFAULT_ARG = 0x5E    # Default argument value
    VAR_ARGS = 0x5F       # Variadic arguments
    
    # ═══════════════════════════════════════════
    # Closures / Generators / Async (0x60-0x6F)
    # ═══════════════════════════════════════════
    MAKE_CLOSURE = 0x60
    MAKE_GENERATOR = 0x61
    MAKE_ASYNC = 0x62
    CAPTURE_UPVALUE = 0x63
    CLOSE_UPVALUE = 0x64
    
    # ═══════════════════════════════════════════
    # Type System (0x70-0x7F)
    # ═══════════════════════════════════════════
    MAKE_STRUCT = 0x70
    MAKE_ENUM = 0x71
    MAKE_IMPL = 0x72
    MAKE_TRAIT = 0x73
    MAKE_VARIANT = 0x74
    TYPE_CHECK = 0x75    # Runtime type check
    TYPE_CAST = 0x76     # Safe cast
    TYPE_OF = 0x77       # Get type object
    GENERIC_INSTANTIATE = 0x78  # Instantiate generic type
    
    # ═══════════════════════════════════════════
    # Concurrency (0x80-0x8F)
    # ═══════════════════════════════════════════
    SPAWN = 0x80          # Spawn concurrent task
    CHANNEL_CREATE = 0x81 # Create channel
    CHANNEL_SEND = 0x82   # Send to channel
    CHANNEL_RECV = 0x83   # Receive from channel
    CHANNEL_CLOSE = 0x84  # Close channel
    FUTURE_GET = 0x85     # Get future value
    SELECT = 0x86         # Channel select
    LOCK = 0x87           # Mutex lock
    UNLOCK = 0x88         # Mutex unlock
    BARRIER = 0x89        # Sync barrier
    
    # ═══════════════════════════════════════════
    # Error Handling (0x90-0x9F)
    # ═══════════════════════════════════════════
    TRY_ENTER = 0x90      # Begin try block
    TRY_EXIT = 0x91       # End try block
    THROW = 0x92          # Throw error
    ASSERT = 0x93         # Assert condition
    DEFER = 0x94          # Defer execution
    CATCH_TYPE = 0x95     # Catch specific type
    FINALLY = 0x96        # Finally block
    
    # ═══════════════════════════════════════════
    # Iterator Protocol (0xA0-0xAF)
    # ═══════════════════════════════════════════
    ITER_INIT = 0xA0      # Initialize iterator
    ITER_NEXT = 0xA1      # Get next item
    ITER_HAS_NEXT = 0xA2  # Check if more items
    FOR_IN = 0xA3         # For-in loop step
    
    # ═══════════════════════════════════════════
    # Pipe / Composition (0xB0-0xBF)
    # ═══════════════════════════════════════════
    PIPE_CALL = 0xB0      # |> pipe operator
    COMPOSE = 0xB1        # >> function composition
    
    # ═══════════════════════════════════════════
    # Import / Module (0xC0-0xCF)
    # ═══════════════════════════════════════════
    IMPORT = 0xC0         # Import module
    IMPORT_FROM = 0xC1    # Import specific names
    EXPORT = 0xC2         # Export symbol
    
    # ═══════════════════════════════════════════
    # Null-Safe (0xD0-0xDF)
    # ═══════════════════════════════════════════
    NULL_SAFE_MEMBER = 0xD0   # obj?.member
    NULL_SAFE_METHOD = 0xD1   # obj?.method()
    NULL_SAFE_INDEX = 0xD2    # obj?[key]
    
    # ═══════════════════════════════════════════
    # Debug / Meta (0xF0-0xFF)
    # ═══════════════════════════════════════════
    DEBUG_PRINT = 0xF0
    DEBUG_STACK = 0xF1
    DEBUG_BREAK = 0xF2    # Breakpoint
    HALT = 0xFF           # Stop execution


# Opcode name lookup
OPCODE_NAMES = {op: op.name for op in OpCode}


@dataclass
class Instruction:
    """A single bytecode instruction with optional operands."""
    opcode: OpCode
    operand: int = 0
    operand2: int = 0
    line: int = 0
    col: int = 0
    
    def __repr__(self):
        name = self.opcode.name
        if self.operand2:
            return f"{name} {self.operand} {self.operand2} (line {self.line})"
        if self.operand:
            return f"{name} {self.operand} (line {self.line})"
        return f"{name} (line {self.line})"


@dataclass
class BytecodeChunk:
    """A compiled unit of bytecode - like a function body or module top-level."""
    name: str
    instructions: List[Instruction] = field(default_factory=list)
    constants: List[Any] = field(default_factory=list)  # constant pool
    local_names: List[str] = field(default_factory=list)  # local var names
    upvalue_names: List[str] = field(default_factory=list)
    local_count: int = 0
    upvalue_count: int = 0
    arity: int = 0
    is_variadic: bool = False
    is_generator: bool = False
    is_async: bool = False
    source_file: str = ""
    
    def emit(self, opcode: OpCode, operand: int = 0, operand2: int = 0,
             line: int = 0, col: int = 0) -> int:
        """Emit an instruction and return its index."""
        idx = len(self.instructions)
        self.instructions.append(Instruction(opcode, operand, operand2, line, col))
        return idx
    
    def add_constant(self, value) -> int:
        """Add a constant to the pool and return its index."""
        if value in self.constants:
            return self.constants.index(value)
        self.constants.append(value)
        return len(self.constants) - 1
    
    def current_offset(self) -> int:
        return len(self.instructions)
    
    def patch_jump(self, offset: int, target: int):
        """Patch a jump instruction's operand to point to target."""
        self.instructions[offset].operand = target
    
    def disassemble(self) -> str:
        """Return a human-readable disassembly of this chunk."""
        lines = [f"=== Chunk: {self.name} ==="]
        lines.append(f"  Locals: {self.local_count}, Upvalues: {self.upvalue_count}, Arity: {self.arity}")
        lines.append(f"  Constants: {len(self.constants)}")
        for i, c in enumerate(self.constants):
            lines.append(f"    [{i}] {type(c).__name__}: {c!r}")
        lines.append("  Instructions:")
        for i, inst in enumerate(self.instructions):
            lines.append(f"    {i:4d} {inst}")
        return "\n".join(lines)


@dataclass
class BytecodeModule:
    """A complete compiled module with multiple chunks."""
    name: str
    main_chunk: BytecodeChunk = None
    function_chunks: List[BytecodeChunk] = field(default_factory=list)
    source_file: str = ""
    
    def all_chunks(self):
        chunks = []
        if self.main_chunk:
            chunks.append(self.main_chunk)
        chunks.extend(self.function_chunks)
        return chunks
