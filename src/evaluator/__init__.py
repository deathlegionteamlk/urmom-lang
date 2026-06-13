"""
Urmom Lang Evaluator/Interpreter.
Walks the AST and executes the program.
"""

from __future__ import annotations
import asyncio
import threading
import queue
import time
import math
import random
import json
import os
import sys
import re
from typing import Any, Optional, Callable
from src.ast import *
from src.lexer.tokens import TokenType


# ========== Runtime Values ==========

class UrmValue:
    """Base class for all Urmom Lang runtime values."""
    pass

class UrmInt(UrmValue):
    def __init__(self, value: int):
        self.value = value
    def __repr__(self): return str(self.value)
    def __eq__(self, other): return isinstance(other, UrmInt) and self.value == other.value
    def __hash__(self): return hash(self.value)

class UrmFloat(UrmValue):
    def __init__(self, value: float):
        self.value = value
    def __repr__(self): return str(self.value)
    def __eq__(self, other): return isinstance(other, UrmFloat) and self.value == other.value
    def __hash__(self): return hash(self.value)

class UrmString(UrmValue):
    def __init__(self, value: str):
        self.value = value
    def __repr__(self): return f'"{self.value}"'
    def __eq__(self, other): return isinstance(other, UrmString) and self.value == other.value
    def __hash__(self): return hash(self.value)

class UrmBool(UrmValue):
    def __init__(self, value: bool):
        self.value = value
    def __repr__(self): return "true" if self.value else "false"
    def __eq__(self, other): return isinstance(other, UrmBool) and self.value == other.value
    def __hash__(self): return hash(self.value)

class UrmNone(UrmValue):
    def __repr__(self): return "none"
    def __eq__(self, other): return isinstance(other, UrmNone)
    def __hash__(self): return hash(None)

URM_NONE = UrmNone()

class UrmArray(UrmValue):
    def __init__(self, elements: list[UrmValue]):
        self.elements = list(elements)
    def __repr__(self): return "[" + ", ".join(str(e) for e in self.elements) + "]"

class UrmDict(UrmValue):
    def __init__(self, pairs: dict):
        self.pairs = dict(pairs)
    def __repr__(self): return "{" + ", ".join(f"{k}: {v}" for k, v in self.pairs.items()) + "}"

class UrmTuple(UrmValue):
    def __init__(self, elements: tuple):
        self.elements = tuple(elements)
    def __repr__(self): return "(" + ", ".join(str(e) for e in self.elements) + ")"

class UrmFunction(UrmValue):
    def __init__(self, name: str, params: list, body: Block, closure: 'Environment',
                 is_async: bool = False):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure
        self.is_async = is_async
    def __repr__(self): return f"<fn {self.name}>"

class UrmBuiltinFn(UrmValue):
    def __init__(self, name: str, fn: Callable):
        self.name = name
        self.fn = fn
    def __repr__(self): return f"<builtin {self.name}>"

class UrmStruct(UrmValue):
    def __init__(self, name: str, fields: dict[str, UrmValue]):
        self.name = name
        self.fields = fields
    def __repr__(self): return f"{self.name}{{{', '.join(f'{k}: {v}' for k, v in self.fields.items())}}}"

class UrmEnumVariant(UrmValue):
    def __init__(self, enum_name: str, variant_name: str, fields: list[UrmValue]):
        self.enum_name = enum_name
        self.variant_name = variant_name
        self.fields = fields
    def __repr__(self): return f"{self.enum_name}.{self.variant_name}"

class UrmChannel(UrmValue):
    def __init__(self, capacity: int = 0):
        self.capacity = capacity
        if capacity > 0:
            self._queue = queue.Queue(maxsize=capacity)
        else:
            self._queue = queue.Queue()
        self._closed = False
    def __repr__(self): return f"<chan cap={self.capacity}>"
    def send(self, value: UrmValue):
        self._queue.put(value, timeout=5.0)
    def receive(self) -> UrmValue:
        return self._queue.get(timeout=5.0)

class UrmFuture(UrmValue):
    def __init__(self, result_event: threading.Event):
        self.result_event = result_event
        self._value = None
    def set_value(self, value: UrmValue):
        self._value = value
        self.result_event.set()
    def get_value(self, timeout: float = 30.0) -> UrmValue:
        self.result_event.wait(timeout=timeout)
        return self._value
    def __repr__(self): return f"<future {'resolved' if self.result_event.is_set() else 'pending'}>"


# ========== Control Flow Signals ==========

class ReturnValue(Exception):
    def __init__(self, value: UrmValue):
        self.value = value

class BreakSignal(Exception):
    pass

class ContinueSignal(Exception):
    pass

class ThrowSignal(Exception):
    def __init__(self, value: UrmValue):
        self.value = value

class DeferStack:
    """Manages deferred function calls."""
    def __init__(self):
        self._calls: list[Callable] = []

    def push(self, fn: Callable):
        self._calls.append(fn)

    def execute_all(self, evaluator: 'Evaluator'):
        """Execute all deferred calls in reverse order."""
        while self._calls:
            fn = self._calls.pop()
            try:
                fn()
            except Exception as e:
                print(f"Error in deferred call: {e}", file=sys.stderr)


# ========== Environment ==========

class Environment:
    """Variable scope environment."""

    def __init__(self, parent: Optional['Environment'] = None):
        self.store: dict[str, UrmValue] = {}
        self.parent = parent
        self._const_names: set[str] = set()
        self._mutability: dict[str, bool] = {}  # True = mutable

    def define(self, name: str, value: UrmValue, mutable: bool = True, const: bool = False):
        self.store[name] = value
        if const:
            self._const_names.add(name)
        self._mutability[name] = mutable if not const else False

    def get(self, name: str) -> Optional[UrmValue]:
        if name in self.store:
            return self.store[name]
        if self.parent:
            return self.parent.get(name)
        return None

    def set(self, name: str, value: UrmValue) -> bool:
        if name in self._const_names:
            return False  # Cannot reassign const
        if name in self.store:
            if not self._mutability.get(name, True):
                return False  # Cannot reassign immutable
            self.store[name] = value
            return True
        if self.parent:
            return self.parent.set(name, value)
        return False

    def has(self, name: str) -> bool:
        if name in self.store:
            return True
        if self.parent:
            return self.parent.has(name)
        return False


# ========== Module System ==========

class ModuleRegistry:
    """Registry for loaded modules."""

    def __init__(self):
        self._modules: dict[str, dict[str, UrmValue]] = {}

    def register(self, name: str, exports: dict[str, UrmValue]):
        self._modules[name] = exports

    def get(self, name: str) -> Optional[dict[str, UrmValue]]:
        return self._modules.get(name)

    def has(self, name: str) -> bool:
        return name in self._modules


# ========== Evaluator ==========

class Evaluator:
    """Main evaluator for Urmom Lang AST."""

    def __init__(self):
        self.global_env = Environment()
        self.modules = ModuleRegistry()
        self._output_buffer: list[str] = []
        self._struct_defs: dict[str, StructDecl] = {}
        self._enum_defs: dict[str, EnumDecl] = {}
        self._impl_methods: dict[str, dict[str, FunctionDecl]] = {}
        self._defer_stack = DeferStack()
        self._register_builtins()
        self._register_stdlib()

    def _register_builtins(self):
        """Register all built-in functions."""
        builtins = {
            "print": self._builtin_print,
            "println": self._builtin_println,
            "printf": self._builtin_printf,
            "len": self._builtin_len,
            "append": self._builtin_append,
            "push": self._builtin_append,
            "pop": self._builtin_pop,
            "type_of": self._builtin_type_of,
            "to_string": self._builtin_to_string,
            "to_int": self._builtin_to_int,
            "to_float": self._builtin_to_float,
            "str": self._builtin_to_string,
            "int": self._builtin_to_int,
            "float": self._builtin_to_float,
            "abs": self._builtin_abs,
            "min": self._builtin_min,
            "max": self._builtin_max,
            "floor": self._builtin_floor,
            "ceil": self._builtin_ceil,
            "round": self._builtin_round,
            "sqrt": self._builtin_sqrt,
            "pow": self._builtin_pow,
            "rand": self._builtin_rand,
            "rand_int": self._builtin_rand_int,
            "range": self._builtin_range,
            "keys": self._builtin_keys,
            "values": self._builtin_values,
            "has_key": self._builtin_has_key,
            "delete": self._builtin_delete,
            "sort": self._builtin_sort,
            "reverse": self._builtin_reverse,
            "map": self._builtin_map,
            "filter": self._builtin_filter,
            "reduce": self._builtin_reduce,
            "join": self._builtin_join,
            "split": self._builtin_split,
            "trim": self._builtin_trim,
            "upper": self._builtin_upper,
            "lower": self._builtin_lower,
            "replace": self._builtin_replace,
            "contains": self._builtin_contains,
            "starts_with": self._builtin_starts_with,
            "ends_with": self._builtin_ends_with,
            "char_at": self._builtin_char_at,
            "substring": self._builtin_substring,
            "index_of": self._builtin_index_of,
            "parse_json": self._builtin_parse_json,
            "to_json": self._builtin_to_json,
            "time_now": self._builtin_time_now,
            "time_format": self._builtin_time_format,
            "sleep": self._builtin_sleep,
            "chan": self._builtin_chan,
            "spawn": self._builtin_spawn,
            "exit": self._builtin_exit,
            "assert": self._builtin_assert,
            "assert_eq": self._builtin_assert_eq,
            "panic": self._builtin_panic,
            "env": self._builtin_env,
            "args": self._builtin_args,
            "copy": self._builtin_copy,
        }
        for name, fn in builtins.items():
            self.global_env.define(name, UrmBuiltinFn(name, fn), mutable=False, const=True)

    # ========== Builtin Implementations ==========

    def _builtin_print(self, *args) -> UrmValue:
        parts = [self._value_to_display(a) for a in args]
        output = " ".join(parts)
        self._output_buffer.append(output)
        print(output, end="")
        return URM_NONE

    def _builtin_println(self, *args) -> UrmValue:
        parts = [self._value_to_display(a) for a in args]
        output = " ".join(parts)
        self._output_buffer.append(output + "\n")
        print(output)
        return URM_NONE

    def _builtin_printf(self, *args) -> UrmValue:
        if not args:
            return URM_NONE
        fmt = self._expect_string(args[0])
        fmt_args = args[1:]
        converted = []
        for a in fmt_args:
            if isinstance(a, UrmInt):
                converted.append(a.value)
            elif isinstance(a, UrmFloat):
                converted.append(a.value)
            elif isinstance(a, UrmString):
                converted.append(a.value)
            elif isinstance(a, UrmBool):
                converted.append(a.value)
            else:
                converted.append(str(a))
        try:
            output = fmt % tuple(converted)
        except TypeError:
            output = fmt.format(*[c.value if hasattr(c, 'value') else c for c in fmt_args])
        self._output_buffer.append(output)
        print(output, end="")
        return URM_NONE

    def _builtin_len(self, *args) -> UrmValue:
        if not args:
            return UrmInt(0)
        val = args[0]
        if isinstance(val, UrmString):
            return UrmInt(len(val.value))
        elif isinstance(val, UrmArray):
            return UrmInt(len(val.elements))
        elif isinstance(val, UrmDict):
            return UrmInt(len(val.pairs))
        elif isinstance(val, UrmTuple):
            return UrmInt(len(val.elements))
        return UrmInt(0)

    def _builtin_append(self, *args) -> UrmValue:
        if len(args) < 2:
            raise ThrowSignal(UrmString("append requires array and value"))
        arr, value = args[0], args[1]
        if isinstance(arr, UrmArray):
            arr.elements.append(value)
            return arr
        raise ThrowSignal(UrmString("append requires an array"))

    def _builtin_pop(self, *args) -> UrmValue:
        if not args:
            raise ThrowSignal(UrmString("pop requires an array"))
        arr = args[0]
        if isinstance(arr, UrmArray) and arr.elements:
            return arr.elements.pop()
        raise ThrowSignal(UrmString("pop: array is empty"))

    def _builtin_type_of(self, *args) -> UrmValue:
        if not args:
            return UrmString("none")
        val = args[0]
        type_map = {
            UrmInt: "int", UrmFloat: "float", UrmString: "string",
            UrmBool: "bool", UrmNone: "none", UrmArray: "array",
            UrmDict: "dict", UrmFunction: "function", UrmBuiltinFn: "function",
            UrmStruct: "struct", UrmChannel: "chan", UrmFuture: "future",
            UrmTuple: "tuple", UrmEnumVariant: "enum_variant",
        }
        for cls, name in type_map.items():
            if isinstance(val, cls):
                return UrmString(name)
        return UrmString("unknown")

    def _builtin_to_string(self, *args) -> UrmValue:
        if not args:
            return UrmString("")
        return UrmString(self._value_to_display(args[0]))

    def _builtin_to_int(self, *args) -> UrmValue:
        if not args:
            return UrmInt(0)
        val = args[0]
        if isinstance(val, UrmInt):
            return val
        elif isinstance(val, UrmFloat):
            return UrmInt(int(val.value))
        elif isinstance(val, UrmString):
            try:
                if val.value.startswith("0x") or val.value.startswith("0X"):
                    return UrmInt(int(val.value, 16))
                return UrmInt(int(val.value))
            except ValueError:
                return UrmInt(0)
        elif isinstance(val, UrmBool):
            return UrmInt(1 if val.value else 0)
        return UrmInt(0)

    def _builtin_to_float(self, *args) -> UrmValue:
        if not args:
            return UrmFloat(0.0)
        val = args[0]
        if isinstance(val, UrmFloat):
            return val
        elif isinstance(val, UrmInt):
            return UrmFloat(float(val.value))
        elif isinstance(val, UrmString):
            try:
                return UrmFloat(float(val.value))
            except ValueError:
                return UrmFloat(0.0)
        return UrmFloat(0.0)

    def _builtin_abs(self, *args) -> UrmValue:
        if not args:
            return UrmInt(0)
        val = args[0]
        if isinstance(val, UrmInt):
            return UrmInt(abs(val.value))
        elif isinstance(val, UrmFloat):
            return UrmFloat(abs(val.value))
        return UrmInt(0)

    def _builtin_min(self, *args) -> UrmValue:
        if len(args) < 2:
            return args[0] if args else URM_NONE
        vals = [self._to_number(a) for a in args]
        min_val = min(vals)
        return UrmInt(int(min_val)) if isinstance(min_val, int) else UrmFloat(min_val)

    def _builtin_max(self, *args) -> UrmValue:
        if len(args) < 2:
            return args[0] if args else URM_NONE
        vals = [self._to_number(a) for a in args]
        max_val = max(vals)
        return UrmInt(int(max_val)) if isinstance(max_val, int) else UrmFloat(max_val)

    def _builtin_floor(self, *args) -> UrmValue:
        if not args:
            return UrmInt(0)
        return UrmInt(int(math.floor(self._to_number(args[0]))))

    def _builtin_ceil(self, *args) -> UrmValue:
        if not args:
            return UrmInt(0)
        return UrmInt(int(math.ceil(self._to_number(args[0]))))

    def _builtin_round(self, *args) -> UrmValue:
        if not args:
            return UrmInt(0)
        n = self._to_number(args[0])
        digits = int(self._to_number(args[1])) if len(args) > 1 else 0
        return UrmFloat(round(n, digits)) if digits > 0 else UrmInt(int(round(n)))

    def _builtin_sqrt(self, *args) -> UrmValue:
        if not args:
            return UrmFloat(0.0)
        return UrmFloat(math.sqrt(self._to_number(args[0])))

    def _builtin_pow(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmInt(0)
        base = self._to_number(args[0])
        exp = self._to_number(args[1])
        result = math.pow(base, exp)
        if result == int(result):
            return UrmInt(int(result))
        return UrmFloat(result)

    def _builtin_rand(self, *args) -> UrmValue:
        if not args:
            return UrmFloat(random.random())
        max_val = self._to_number(args[0])
        return UrmFloat(random.random() * max_val)

    def _builtin_rand_int(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmInt(0)
        min_val = int(self._to_number(args[0]))
        max_val = int(self._to_number(args[1]))
        return UrmInt(random.randint(min_val, max_val))

    def _builtin_range(self, *args) -> UrmValue:
        start, end, step = 0, 0, 1
        if len(args) == 1:
            end = int(self._to_number(args[0]))
        elif len(args) == 2:
            start = int(self._to_number(args[0]))
            end = int(self._to_number(args[1]))
        elif len(args) >= 3:
            start = int(self._to_number(args[0]))
            end = int(self._to_number(args[1]))
            step = int(self._to_number(args[2]))
        if step == 0:
            step = 1
        elements = [UrmInt(i) for i in range(start, end, step)]
        return UrmArray(elements)

    def _builtin_keys(self, *args) -> UrmValue:
        if not args or not isinstance(args[0], UrmDict):
            return UrmArray([])
        return UrmArray([UrmString(k) for k in args[0].pairs.keys()])

    def _builtin_values(self, *args) -> UrmValue:
        if not args or not isinstance(args[0], UrmDict):
            return UrmArray([])
        return UrmArray(list(args[0].pairs.values()))

    def _builtin_has_key(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmBool(False)
        d, key = args[0], args[1]
        if isinstance(d, UrmDict):
            key_str = self._value_to_display(key)
            return UrmBool(key_str in d.pairs)
        return UrmBool(False)

    def _builtin_delete(self, *args) -> UrmValue:
        if len(args) < 2:
            return URM_NONE
        d, key = args[0], args[1]
        if isinstance(d, UrmDict):
            key_str = self._value_to_display(key)
            d.pairs.pop(key_str, None)
        return URM_NONE

    def _builtin_sort(self, *args) -> UrmValue:
        if not args:
            return UrmArray([])
        arr = args[0]
        if isinstance(arr, UrmArray):
            try:
                sorted_elems = sorted(arr.elements, key=lambda x: self._to_number(x) if isinstance(x, (UrmInt, UrmFloat)) else str(x))
                return UrmArray(sorted_elems)
            except (TypeError, ValueError):
                sorted_elems = sorted(arr.elements, key=lambda x: self._value_to_display(x))
                return UrmArray(sorted_elems)
        return arr

    def _builtin_reverse(self, *args) -> UrmValue:
        if not args:
            return UrmArray([])
        arr = args[0]
        if isinstance(arr, UrmArray):
            arr.elements.reverse()
        return arr

    def _builtin_map(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmArray([])
        fn, arr = args[0], args[1]
        if isinstance(arr, UrmArray) and isinstance(fn, (UrmFunction, UrmBuiltinFn)):
            results = []
            for elem in arr.elements:
                results.append(self._call_function(fn, [elem]))
            return UrmArray(results)
        return UrmArray([])

    def _builtin_filter(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmArray([])
        fn, arr = args[0], args[1]
        if isinstance(arr, UrmArray) and isinstance(fn, (UrmFunction, UrmBuiltinFn)):
            results = []
            for elem in arr.elements:
                result = self._call_function(fn, [elem])
                if self._is_truthy(result):
                    results.append(elem)
            return UrmArray(results)
        return UrmArray([])

    def _builtin_reduce(self, *args) -> UrmValue:
        if len(args) < 2:
            return URM_NONE
        fn, arr = args[0], args[1]
        init = args[2] if len(args) > 2 else None
        if isinstance(arr, UrmArray) and isinstance(fn, (UrmFunction, UrmBuiltinFn)):
            acc = init if init is not None else arr.elements[0]
            start = 0 if init is not None else 1
            for i in range(start, len(arr.elements)):
                acc = self._call_function(fn, [acc, arr.elements[i]])
            return acc
        return URM_NONE

    def _builtin_join(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmString("")
        sep = self._expect_string(args[0])
        arr = args[1]
        if isinstance(arr, UrmArray):
            return UrmString(sep.join(self._value_to_display(e) for e in arr.elements))
        return UrmString("")

    def _builtin_split(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmArray([])
        s = self._expect_string(args[0])
        sep = self._expect_string(args[1])
        return UrmArray([UrmString(p) for p in s.split(sep)])

    def _builtin_trim(self, *args) -> UrmValue:
        if not args:
            return UrmString("")
        return UrmString(self._expect_string(args[0]).strip())

    def _builtin_upper(self, *args) -> UrmValue:
        if not args:
            return UrmString("")
        return UrmString(self._expect_string(args[0]).upper())

    def _builtin_lower(self, *args) -> UrmValue:
        if not args:
            return UrmString("")
        return UrmString(self._expect_string(args[0]).lower())

    def _builtin_replace(self, *args) -> UrmValue:
        if len(args) < 3:
            return UrmString("")
        s = self._expect_string(args[0])
        old = self._expect_string(args[1])
        new = self._expect_string(args[2])
        return UrmString(s.replace(old, new))

    def _builtin_contains(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmBool(False)
        s = self._expect_string(args[0])
        sub = self._expect_string(args[1])
        return UrmBool(sub in s)

    def _builtin_starts_with(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmBool(False)
        return UrmBool(self._expect_string(args[0]).startswith(self._expect_string(args[1])))

    def _builtin_ends_with(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmBool(False)
        return UrmBool(self._expect_string(args[0]).endswith(self._expect_string(args[1])))

    def _builtin_char_at(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmString("")
        s = self._expect_string(args[0])
        idx = int(self._to_number(args[1]))
        if 0 <= idx < len(s):
            return UrmString(s[idx])
        return UrmString("")

    def _builtin_substring(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmString("")
        s = self._expect_string(args[0])
        start = int(self._to_number(args[1]))
        end = int(self._to_number(args[2])) if len(args) > 2 else len(s)
        return UrmString(s[start:end])

    def _builtin_index_of(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmInt(-1)
        s = self._expect_string(args[0])
        sub = self._expect_string(args[1])
        return UrmInt(s.find(sub))

    def _builtin_parse_json(self, *args) -> UrmValue:
        if not args:
            return URM_NONE
        try:
            data = json.loads(self._expect_string(args[0]))
            return self._python_to_urm(data)
        except json.JSONDecodeError:
            return URM_NONE

    def _builtin_to_json(self, *args) -> UrmValue:
        if not args:
            return UrmString("null")
        try:
            data = self._urm_to_python(args[0])
            return UrmString(json.dumps(data, indent=2))
        except (TypeError, ValueError):
            return UrmString("null")

    def _builtin_time_now(self, *args) -> UrmValue:
        return UrmFloat(time.time())

    def _builtin_time_format(self, *args) -> UrmValue:
        if not args:
            return UrmString(time.strftime("%Y-%m-%d %H:%M:%S"))
        fmt = self._expect_string(args[0])
        timestamp = self._to_number(args[1]) if len(args) > 1 else time.time()
        return UrmString(time.strftime(fmt, time.localtime(timestamp)))

    def _builtin_sleep(self, *args) -> UrmValue:
        if args:
            seconds = self._to_number(args[0])
            time.sleep(seconds)
        return URM_NONE

    def _builtin_chan(self, *args) -> UrmValue:
        cap = int(self._to_number(args[0])) if args else 0
        return UrmChannel(capacity=cap)

    def _builtin_spawn(self, *args) -> UrmValue:
        if not args:
            raise ThrowSignal(UrmString("spawn requires a function"))
        fn = args[0]
        fn_args = list(args[1:])
        event = threading.Event()
        future = UrmFuture(event)

        def run():
            try:
                result = self._call_function(fn, fn_args)
                future.set_value(result)
            except ThrowSignal as e:
                future.set_value(e.value)
            except Exception as e:
                future.set_value(UrmString(str(e)))

        t = threading.Thread(target=run, daemon=True)
        t.start()
        return future

    def _builtin_exit(self, *args) -> UrmValue:
        code = int(self._to_number(args[0])) if args else 0
        sys.exit(code)

    def _builtin_assert(self, *args) -> UrmValue:
        if not args:
            raise ThrowSignal(UrmString("assert requires a condition"))
        if not self._is_truthy(args[0]):
            msg = self._expect_string(args[1]) if len(args) > 1 else "Assertion failed"
            raise ThrowSignal(UrmString(f"Assertion error: {msg}"))
        return URM_NONE

    def _builtin_assert_eq(self, *args) -> UrmValue:
        if len(args) < 2:
            raise ThrowSignal(UrmString("assert_eq requires two values"))
        if not self._values_equal(args[0], args[1]):
            msg = f"Assertion error: {self._value_to_display(args[0])} != {self._value_to_display(args[1])}"
            raise ThrowSignal(UrmString(msg))
        return URM_NONE

    def _builtin_panic(self, *args) -> UrmValue:
        msg = self._expect_string(args[0]) if args else "panic!"
        raise ThrowSignal(UrmString(f"PANIC: {msg}"))

    def _builtin_env(self, *args) -> UrmValue:
        if args:
            key = self._expect_string(args[0])
            val = os.environ.get(key, "")
            return UrmString(val)
        return UrmDict({k: UrmString(v) for k, v in os.environ.items()})

    def _builtin_args(self, *args) -> UrmValue:
        return UrmArray([UrmString(a) for a in sys.argv])

    def _builtin_copy(self, *args) -> UrmValue:
        if not args:
            return URM_NONE
        val = args[0]
        if isinstance(val, UrmArray):
            return UrmArray(list(val.elements))
        elif isinstance(val, UrmDict):
            return UrmDict(dict(val.pairs))
        return val

    # ========== Helper Methods ==========

    def _value_to_display(self, val: UrmValue) -> str:
        if isinstance(val, UrmInt):
            return str(val.value)
        elif isinstance(val, UrmFloat):
            if val.value == int(val.value):
                return f"{val.value:.1f}"
            return str(val.value)
        elif isinstance(val, UrmString):
            return val.value
        elif isinstance(val, UrmBool):
            return "true" if val.value else "false"
        elif isinstance(val, UrmNone):
            return "none"
        elif isinstance(val, UrmArray):
            return "[" + ", ".join(self._value_to_display(e) for e in val.elements) + "]"
        elif isinstance(val, UrmDict):
            return "{" + ", ".join(f"{self._value_to_display(UrmString(k))}: {self._value_to_display(v)}" for k, v in val.pairs.items()) + "}"
        elif isinstance(val, UrmTuple):
            return "(" + ", ".join(self._value_to_display(e) for e in val.elements) + ")"
        elif isinstance(val, UrmFunction):
            return f"<fn {val.name}>"
        elif isinstance(val, UrmBuiltinFn):
            return f"<builtin {val.name}>"
        elif isinstance(val, UrmStruct):
            return str(val)
        elif isinstance(val, UrmChannel):
            return str(val)
        elif isinstance(val, UrmFuture):
            return str(val)
        elif isinstance(val, UrmEnumVariant):
            return str(val)
        return str(val)

    def _expect_string(self, val: UrmValue) -> str:
        if isinstance(val, UrmString):
            return val.value
        return self._value_to_display(val)

    def _to_number(self, val: UrmValue) -> float:
        if isinstance(val, UrmInt):
            return float(val.value)
        elif isinstance(val, UrmFloat):
            return val.value
        elif isinstance(val, UrmBool):
            return 1.0 if val.value else 0.0
        elif isinstance(val, UrmString):
            try:
                return float(val.value)
            except ValueError:
                return 0.0
        return 0.0

    def _is_truthy(self, val: UrmValue) -> bool:
        if isinstance(val, UrmBool):
            return val.value
        elif isinstance(val, UrmInt):
            return val.value != 0
        elif isinstance(val, UrmFloat):
            return val.value != 0.0
        elif isinstance(val, UrmString):
            return len(val.value) > 0
        elif isinstance(val, UrmNone):
            return False
        elif isinstance(val, UrmArray):
            return len(val.elements) > 0
        elif isinstance(val, UrmDict):
            return len(val.pairs) > 0
        return True

    def _values_equal(self, a: UrmValue, b: UrmValue) -> bool:
        if type(a) != type(b):
            # Allow int/float comparison
            if isinstance(a, (UrmInt, UrmFloat)) and isinstance(b, (UrmInt, UrmFloat)):
                return self._to_number(a) == self._to_number(b)
            return False
        if isinstance(a, UrmInt):
            return a.value == b.value
        elif isinstance(a, UrmFloat):
            return a.value == b.value
        elif isinstance(a, UrmString):
            return a.value == b.value
        elif isinstance(a, UrmBool):
            return a.value == b.value
        elif isinstance(a, UrmNone):
            return True
        elif isinstance(a, UrmArray):
            if len(a.elements) != len(b.elements):
                return False
            return all(self._values_equal(x, y) for x, y in zip(a.elements, b.elements))
        elif isinstance(a, UrmDict):
            if set(a.pairs.keys()) != set(b.pairs.keys()):
                return False
            return all(self._values_equal(a.pairs[k], b.pairs[k]) for k in a.pairs)
        return a is b

    def _python_to_urm(self, data) -> UrmValue:
        if data is None:
            return URM_NONE
        elif isinstance(data, bool):
            return UrmBool(data)
        elif isinstance(data, int):
            return UrmInt(data)
        elif isinstance(data, float):
            return UrmFloat(data)
        elif isinstance(data, str):
            return UrmString(data)
        elif isinstance(data, list):
            return UrmArray([self._python_to_urm(item) for item in data])
        elif isinstance(data, dict):
            return UrmDict({str(k): self._python_to_urm(v) for k, v in data.items()})
        return UrmString(str(data))

    def _urm_to_python(self, val: UrmValue):
        if isinstance(val, UrmNone):
            return None
        elif isinstance(val, UrmBool):
            return val.value
        elif isinstance(val, UrmInt):
            return val.value
        elif isinstance(val, UrmFloat):
            return val.value
        elif isinstance(val, UrmString):
            return val.value
        elif isinstance(val, UrmArray):
            return [self._urm_to_python(e) for e in val.elements]
        elif isinstance(val, UrmDict):
            return {k: self._urm_to_python(v) for k, v in val.pairs.items()}
        return str(val)

    def _call_function(self, fn: UrmValue, args: list[UrmValue]) -> UrmValue:
        if isinstance(fn, UrmBuiltinFn):
            return fn.fn(*args)
        elif isinstance(fn, UrmFunction):
            env = Environment(parent=fn.closure)
            # Bind parameters
            for i, param in enumerate(fn.params):
                if i < len(args):
                    env.define(param.name, args[i], mutable=True)
                elif param.default_value is not None:
                    env.define(param.name, self._eval_expr(param.default_value, env), mutable=True)
                elif param.is_variadic:
                    env.define(param.name, UrmArray(args[i:]), mutable=True)
                else:
                    env.define(param.name, URM_NONE, mutable=True)
            # Handle variadic
            if fn.params and fn.params[-1].is_variadic:
                last = fn.params[-1]
                remaining = args[len(fn.params) - 1:]
                env.define(last.name, UrmArray(remaining), mutable=True)
            try:
                result = self._eval_block(fn.body, env)
                return result
            except ReturnValue as rv:
                return rv.value
        raise ThrowSignal(UrmString(f"Cannot call {type(fn).__name__}"))

    # ========== Standard Library Registration ==========

    def _register_stdlib(self):
        """Register standard library modules."""
        self.modules.register("std.io", {
            "print": UrmBuiltinFn("print", self._builtin_print),
            "println": UrmBuiltinFn("println", self._builtin_println),
            "read_line": UrmBuiltinFn("read_line", lambda: UrmString(input())),
        })
        self.modules.register("std.fs", {
            "read_file": UrmBuiltinFn("read_file", self._stdlib_fs_read_file),
            "write_file": UrmBuiltinFn("write_file", self._stdlib_fs_write_file),
            "exists": UrmBuiltinFn("exists", self._stdlib_fs_exists),
            "mkdir": UrmBuiltinFn("mkdir", self._stdlib_fs_mkdir),
            "list_dir": UrmBuiltinFn("list_dir", self._stdlib_fs_list_dir),
            "remove": UrmBuiltinFn("remove", self._stdlib_fs_remove),
            "is_dir": UrmBuiltinFn("is_dir", self._stdlib_fs_is_dir),
            "is_file": UrmBuiltinFn("is_file", self._stdlib_fs_is_file),
            "size": UrmBuiltinFn("size", self._stdlib_fs_size),
            "copy": UrmBuiltinFn("copy", self._stdlib_fs_copy),
            "rename": UrmBuiltinFn("rename", self._stdlib_fs_rename),
            "cwd": UrmBuiltinFn("cwd", lambda: UrmString(os.getcwd())),
            "path_join": UrmBuiltinFn("path_join", self._stdlib_fs_path_join),
            "path_split": UrmBuiltinFn("path_split", self._stdlib_fs_path_split),
        })
        self.modules.register("std.net", {
            "http_get": UrmBuiltinFn("http_get", self._stdlib_net_http_get),
            "http_post": UrmBuiltinFn("http_post", self._stdlib_net_http_post),
            "tcp_listen": UrmBuiltinFn("tcp_listen", self._stdlib_net_tcp_listen),
            "resolve_host": UrmBuiltinFn("resolve_host", self._stdlib_net_resolve),
        })
        self.modules.register("std.data", {
            "parse_json": UrmBuiltinFn("parse_json", self._builtin_parse_json),
            "to_json": UrmBuiltinFn("to_json", self._builtin_to_json),
            "parse_csv": UrmBuiltinFn("parse_csv", self._stdlib_data_parse_csv),
            "to_csv": UrmBuiltinFn("to_csv", self._stdlib_data_to_csv),
            "encode_base64": UrmBuiltinFn("encode_base64", self._stdlib_data_encode_b64),
            "decode_base64": UrmBuiltinFn("decode_base64", self._stdlib_data_decode_b64),
        })
        self.modules.register("std.math", {
            "pi": UrmFloat(math.pi),
            "e": UrmFloat(math.e),
            "inf": UrmFloat(math.inf),
            "sin": UrmBuiltinFn("sin", lambda *a: UrmFloat(math.sin(self._to_number(a[0]))) if a else UrmFloat(0.0)),
            "cos": UrmBuiltinFn("cos", lambda *a: UrmFloat(math.cos(self._to_number(a[0]))) if a else UrmFloat(0.0)),
            "tan": UrmBuiltinFn("tan", lambda *a: UrmFloat(math.tan(self._to_number(a[0]))) if a else UrmFloat(0.0)),
            "log": UrmBuiltinFn("log", lambda *a: UrmFloat(math.log(self._to_number(a[0]))) if a else UrmFloat(0.0)),
            "log2": UrmBuiltinFn("log2", lambda *a: UrmFloat(math.log2(self._to_number(a[0]))) if a else UrmFloat(0.0)),
            "log10": UrmBuiltinFn("log10", lambda *a: UrmFloat(math.log10(self._to_number(a[0]))) if a else UrmFloat(0.0)),
            "abs": UrmBuiltinFn("abs", self._builtin_abs),
            "floor": UrmBuiltinFn("floor", self._builtin_floor),
            "ceil": UrmBuiltinFn("ceil", self._builtin_ceil),
            "round": UrmBuiltinFn("round", self._builtin_round),
            "sqrt": UrmBuiltinFn("sqrt", self._builtin_sqrt),
            "pow": UrmBuiltinFn("pow", self._builtin_pow),
            "min": UrmBuiltinFn("min", self._builtin_min),
            "max": UrmBuiltinFn("max", self._builtin_max),
        })
        self.modules.register("std.time", {
            "now": UrmBuiltinFn("now", self._builtin_time_now),
            "format": UrmBuiltinFn("format", self._builtin_time_format),
            "sleep": UrmBuiltinFn("sleep", self._builtin_sleep),
            "parse": UrmBuiltinFn("parse", self._stdlib_time_parse),
        })
        self.modules.register("std.rand", {
            "int": UrmBuiltinFn("int", self._builtin_rand_int),
            "float": UrmBuiltinFn("float", self._builtin_rand),
            "choice": UrmBuiltinFn("choice", self._stdlib_rand_choice),
            "shuffle": UrmBuiltinFn("shuffle", self._stdlib_rand_shuffle),
            "seed": UrmBuiltinFn("seed", lambda *a: (random.seed(int(self._to_number(a[0]))), URM_NONE)[1] if a else URM_NONE),
        })
        self.modules.register("std.regex", {
            "match": UrmBuiltinFn("match", self._stdlib_regex_match),
            "find_all": UrmBuiltinFn("find_all", self._stdlib_regex_find_all),
            "replace": UrmBuiltinFn("replace", self._stdlib_regex_replace),
        })
        self.modules.register("std.concurrency", {
            "spawn": UrmBuiltinFn("spawn", self._builtin_spawn),
            "chan": UrmBuiltinFn("chan", self._builtin_chan),
        })

    # ========== Standard Library Implementations ==========

    def _stdlib_fs_read_file(self, *args) -> UrmValue:
        if not args:
            return UrmString("")
        path = self._expect_string(args[0])
        try:
            with open(path, 'r') as f:
                return UrmString(f.read())
        except FileNotFoundError:
            raise ThrowSignal(UrmString(f"File not found: {path}"))
        except Exception as e:
            raise ThrowSignal(UrmString(f"Error reading file: {e}"))

    def _stdlib_fs_write_file(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmBool(False)
        path = self._expect_string(args[0])
        content = self._expect_string(args[1])
        try:
            with open(path, 'w') as f:
                f.write(content)
            return UrmBool(True)
        except Exception as e:
            raise ThrowSignal(UrmString(f"Error writing file: {e}"))

    def _stdlib_fs_exists(self, *args) -> UrmValue:
        if not args:
            return UrmBool(False)
        return UrmBool(os.path.exists(self._expect_string(args[0])))

    def _stdlib_fs_mkdir(self, *args) -> UrmValue:
        if not args:
            return UrmBool(False)
        try:
            os.makedirs(self._expect_string(args[0]), exist_ok=True)
            return UrmBool(True)
        except Exception:
            return UrmBool(False)

    def _stdlib_fs_list_dir(self, *args) -> UrmValue:
        if not args:
            return UrmArray([])
        try:
            path = self._expect_string(args[0])
            entries = os.listdir(path)
            return UrmArray([UrmString(e) for e in entries])
        except Exception:
            return UrmArray([])

    def _stdlib_fs_remove(self, *args) -> UrmValue:
        if not args:
            return UrmBool(False)
        try:
            path = self._expect_string(args[0])
            if os.path.isdir(path):
                os.rmdir(path)
            else:
                os.remove(path)
            return UrmBool(True)
        except Exception:
            return UrmBool(False)

    def _stdlib_fs_is_dir(self, *args) -> UrmValue:
        if not args:
            return UrmBool(False)
        return UrmBool(os.path.isdir(self._expect_string(args[0])))

    def _stdlib_fs_is_file(self, *args) -> UrmValue:
        if not args:
            return UrmBool(False)
        return UrmBool(os.path.isfile(self._expect_string(args[0])))

    def _stdlib_fs_size(self, *args) -> UrmValue:
        if not args:
            return UrmInt(0)
        try:
            return UrmInt(os.path.getsize(self._expect_string(args[0])))
        except Exception:
            return UrmInt(0)

    def _stdlib_fs_copy(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmBool(False)
        try:
            import shutil
            shutil.copy2(self._expect_string(args[0]), self._expect_string(args[1]))
            return UrmBool(True)
        except Exception:
            return UrmBool(False)

    def _stdlib_fs_rename(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmBool(False)
        try:
            os.rename(self._expect_string(args[0]), self._expect_string(args[1]))
            return UrmBool(True)
        except Exception:
            return UrmBool(False)

    def _stdlib_fs_path_join(self, *args) -> UrmValue:
        parts = [self._expect_string(a) for a in args]
        return UrmString(os.path.join(*parts))

    def _stdlib_fs_path_split(self, *args) -> UrmValue:
        if not args:
            return UrmTuple((UrmString(""), UrmString("")))
        head, tail = os.path.split(self._expect_string(args[0]))
        return UrmTuple((UrmString(head), UrmString(tail)))

    def _stdlib_net_http_get(self, *args) -> UrmValue:
        if not args:
            return UrmString("")
        url = self._expect_string(args[0])
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = resp.read().decode('utf-8')
                return UrmString(data)
        except Exception as e:
            raise ThrowSignal(UrmString(f"HTTP GET error: {e}"))

    def _stdlib_net_http_post(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmString("")
        url = self._expect_string(args[0])
        body = self._expect_string(args[1])
        try:
            import urllib.request
            req = urllib.request.Request(url, data=body.encode('utf-8'), method='POST')
            with urllib.request.urlopen(req, timeout=10) as resp:
                return UrmString(resp.read().decode('utf-8'))
        except Exception as e:
            raise ThrowSignal(UrmString(f"HTTP POST error: {e}"))

    def _stdlib_net_tcp_listen(self, *args) -> UrmValue:
        return UrmString("TCP listener stub - not yet fully implemented in interpreter mode")

    def _stdlib_net_resolve(self, *args) -> UrmValue:
        if not args:
            return UrmString("")
        import socket
        try:
            host = self._expect_string(args[0])
            result = socket.gethostbyname(host)
            return UrmString(result)
        except Exception as e:
            raise ThrowSignal(UrmString(f"DNS resolution error: {e}"))

    def _stdlib_data_parse_csv(self, *args) -> UrmValue:
        if not args:
            return UrmArray([])
        import csv
        import io
        try:
            text = self._expect_string(args[0])
            reader = csv.reader(io.StringIO(text))
            rows = [[UrmString(cell) for cell in row] for row in reader]
            return UrmArray([UrmArray(row) for row in rows])
        except Exception:
            return UrmArray([])

    def _stdlib_data_to_csv(self, *args) -> UrmValue:
        if not args:
            return UrmString("")
        import csv
        import io
        try:
            arr = args[0]
            if isinstance(arr, UrmArray):
                output = io.StringIO()
                writer = csv.writer(output)
                for row in arr.elements:
                    if isinstance(row, UrmArray):
                        writer.writerow([self._expect_string(e) for e in row.elements])
                    else:
                        writer.writerow([self._expect_string(row)])
                return UrmString(output.getvalue())
        except Exception:
            pass
        return UrmString("")

    def _stdlib_data_encode_b64(self, *args) -> UrmValue:
        if not args:
            return UrmString("")
        import base64
        data = self._expect_string(args[0])
        return UrmString(base64.b64encode(data.encode()).decode())

    def _stdlib_data_decode_b64(self, *args) -> UrmValue:
        if not args:
            return UrmString("")
        import base64
        data = self._expect_string(args[0])
        try:
            return UrmString(base64.b64decode(data.encode()).decode())
        except Exception:
            return UrmString("")

    def _stdlib_time_parse(self, *args) -> UrmValue:
        if not args:
            return UrmFloat(0.0)
        try:
            fmt = self._expect_string(args[0])
            s = self._expect_string(args[1])
            return UrmFloat(time.mktime(time.strptime(s, fmt)))
        except Exception:
            return UrmFloat(0.0)

    def _stdlib_rand_choice(self, *args) -> UrmValue:
        if not args:
            return URM_NONE
        arr = args[0]
        if isinstance(arr, UrmArray) and arr.elements:
            return random.choice(arr.elements)
        return URM_NONE

    def _stdlib_rand_shuffle(self, *args) -> UrmValue:
        if not args:
            return UrmArray([])
        arr = args[0]
        if isinstance(arr, UrmArray):
            random.shuffle(arr.elements)
        return arr

    def _stdlib_regex_match(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmBool(False)
        pattern = self._expect_string(args[0])
        text = self._expect_string(args[1])
        return UrmBool(bool(re.match(pattern, text)))

    def _stdlib_regex_find_all(self, *args) -> UrmValue:
        if len(args) < 2:
            return UrmArray([])
        pattern = self._expect_string(args[0])
        text = self._expect_string(args[1])
        matches = re.findall(pattern, text)
        return UrmArray([UrmString(m) if isinstance(m, str) else UrmArray([UrmString(g) for g in m]) for m in matches])

    def _stdlib_regex_replace(self, *args) -> UrmValue:
        if len(args) < 3:
            return UrmString("")
        pattern = self._expect_string(args[0])
        replacement = self._expect_string(args[1])
        text = self._expect_string(args[2])
        return UrmString(re.sub(pattern, replacement, text))

    # ========== Main Evaluation ==========

    def run(self, program: Program) -> UrmValue:
        """Run a parsed program and return the result."""
        # Process imports
        for imp in program.imports:
            self._process_import(imp)

        # Process declarations
        for decl in program.declarations:
            self._eval_declaration(decl, self.global_env)

        # Execute statements
        result = URM_NONE
        for stmt in program.statements:
            result = self._eval_statement(stmt, self.global_env)

        return result

    def eval_source(self, source: str, filename: str = "<stdin>") -> UrmValue:
        """Parse and evaluate source code."""
        from src.lexer import Lexer
        from src.parser import Parser

        lexer = Lexer(source, filename)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse()
        return self.run(program)

    def _process_import(self, imp: ImportDecl):
        """Process an import declaration."""
        module = self.modules.get(imp.module_path)
        if module is None:
            # Try to load from file
            file_path = imp.module_path.replace(".", "/") + ".urm"
            if os.path.exists(file_path):
                self._load_module_file(imp.module_path, file_path)
                module = self.modules.get(imp.module_path)
        if module is None:
            raise ThrowSignal(UrmString(f"Module not found: {imp.module_path}"))

        if imp.items:
            for item_name in imp.items:
                if item_name in module:
                    self.global_env.define(item_name, module[item_name])
                else:
                    raise ThrowSignal(UrmString(f"'{item_name}' not found in {imp.module_path}"))
        else:
            alias = imp.alias or imp.module_path.split(".")[-1]
            self.global_env.define(alias, UrmDict(module))

    def _load_module_file(self, module_name: str, file_path: str):
        """Load a module from a .urm file."""
        from src.lexer import Lexer
        from src.parser import Parser

        with open(file_path, 'r') as f:
            source = f.read()
        lexer = Lexer(source, file_path)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        program = parser.parse()

        # Create a new evaluator for the module
        module_env = Environment(parent=self.global_env)
        exports = {}
        for decl in program.declarations:
            self._eval_declaration(decl, module_env)
        for stmt in program.statements:
            self._eval_statement(stmt, module_env)

        # Export public items
        for name, value in module_env.store.items():
            exports[name] = value

        self.modules.register(module_name, exports)

    # ========== Declaration Evaluation ==========

    def _eval_declaration(self, decl, env: Environment):
        if isinstance(decl, FunctionDecl):
            fn = UrmFunction(decl.name, decl.params, decl.body, env, decl.is_async)
            env.define(decl.name, fn, mutable=not decl.is_public)
        elif isinstance(decl, StructDecl):
            self._struct_defs[decl.name] = decl
            # Create a constructor function
            struct_decl = decl
            def make_struct(*args, _decl=struct_decl):
                fields = {}
                for i, field in enumerate(_decl.fields):
                    if i < len(args):
                        fields[field.name] = args[i]
                    elif field.default_value is not None:
                        fields[field.name] = self._eval_expr(field.default_value, env)
                    else:
                        fields[field.name] = URM_NONE
                return UrmStruct(_decl.name, fields)
            env.define(decl.name, UrmBuiltinFn(decl.name, make_struct))
        elif isinstance(decl, EnumDecl):
            self._enum_defs[decl.name] = decl
            for variant in decl.variants:
                enum_name = decl.name
                variant_name = variant.name
                variant_fields = variant.fields
                def make_variant(*args, _en=enum_name, _vn=variant_name, _vf=variant_fields):
                    return UrmEnumVariant(_en, _vn, list(args))
                env.define(variant_name, UrmBuiltinFn(variant_name, make_variant))
        elif isinstance(decl, ImplDecl):
            if decl.target not in self._impl_methods:
                self._impl_methods[decl.target] = {}
            for method in decl.methods:
                self._impl_methods[decl.target][method.name] = method
        elif isinstance(decl, TraitDecl):
            # Store trait definition for reference
            env.define(decl.name, UrmString(f"<trait {decl.name}>"))
        elif isinstance(decl, TypeAliasDecl):
            env.define(decl.name, UrmString(f"<type {decl.name}>"))

    # ========== Statement Evaluation ==========

    def _eval_statement(self, stmt, env: Environment) -> UrmValue:
        if isinstance(stmt, LetStmt):
            value = self._eval_expr(stmt.value, env) if stmt.value else URM_NONE
            env.define(stmt.name, value, mutable=stmt.mutable)
            return value
        elif isinstance(stmt, ConstStmt):
            value = self._eval_expr(stmt.value, env)
            env.define(stmt.name, value, mutable=False, const=True)
            return value
        elif isinstance(stmt, AssignStmt):
            value = self._eval_expr(stmt.value, env)
            if isinstance(stmt.target, Identifier):
                if not env.set(stmt.target.name, value):
                    raise ThrowSignal(UrmString(f"Cannot assign to '{stmt.target.name}'"))
            elif isinstance(stmt.target, IndexExpr):
                obj = self._eval_expr(stmt.target.obj, env)
                idx = self._eval_expr(stmt.target.index, env)
                if isinstance(obj, UrmArray):
                    idx_val = int(self._to_number(idx))
                    if 0 <= idx_val < len(obj.elements):
                        obj.elements[idx_val] = value
                    else:
                        raise ThrowSignal(UrmString(f"Index {idx_val} out of range"))
                elif isinstance(obj, UrmDict):
                    key_str = self._expect_string(idx)
                    obj.pairs[key_str] = value
            elif isinstance(stmt.target, MemberExpr):
                obj = self._eval_expr(stmt.target.obj, env)
                if isinstance(obj, UrmStruct):
                    obj.fields[stmt.target.member] = value
            return value
        elif isinstance(stmt, CompoundAssignStmt):
            current = self._eval_expr(stmt.target, env)
            add_val = self._eval_expr(stmt.value, env)
            op_map = {"+=": "+", "-=": "-", "*=": "*", "/=": "/"}
            new_val = self._eval_infix(op_map.get(stmt.operator, "+"), current, add_val)
            if isinstance(stmt.target, Identifier):
                env.set(stmt.target.name, new_val)
            return new_val
        elif isinstance(stmt, ReturnStmt):
            value = self._eval_expr(stmt.value, env) if stmt.value else URM_NONE
            raise ReturnValue(value)
        elif isinstance(stmt, BreakStmt):
            raise BreakSignal()
        elif isinstance(stmt, ContinueStmt):
            raise ContinueSignal()
        elif isinstance(stmt, ThrowStmt):
            value = self._eval_expr(stmt.value, env)
            raise ThrowSignal(value)
        elif isinstance(stmt, DeferStmt):
            saved_call = stmt.call
            self._defer_stack.push(lambda c=saved_call, e=env: self._eval_call(c, e))
            return URM_NONE
        elif isinstance(stmt, IfStmt):
            return self._eval_if(stmt, env)
        elif isinstance(stmt, WhileStmt):
            return self._eval_while(stmt, env)
        elif isinstance(stmt, ForInStmt):
            return self._eval_for_in(stmt, env)
        elif isinstance(stmt, ForStmt):
            return self._eval_for(stmt, env)
        elif isinstance(stmt, MatchStmt):
            return self._eval_match(stmt, env)
        elif isinstance(stmt, TryCatchStmt):
            return self._eval_try_catch(stmt, env)
        elif isinstance(stmt, Block):
            return self._eval_block(stmt, env)
        elif isinstance(stmt, ExpressionStmt):
            return self._eval_expr(stmt.expression, env)
        return URM_NONE

    # ========== Expression Evaluation ==========

    def _eval_expr(self, expr, env: Environment) -> UrmValue:
        if isinstance(expr, IntLiteral):
            return UrmInt(expr.value)
        elif isinstance(expr, FloatLiteral):
            return UrmFloat(expr.value)
        elif isinstance(expr, StringLiteral):
            return UrmString(expr.value)
        elif isinstance(expr, BoolLiteral):
            return UrmBool(expr.value)
        elif isinstance(expr, NoneLiteral):
            return URM_NONE
        elif isinstance(expr, Identifier):
            val = env.get(expr.name)
            if val is None:
                raise ThrowSignal(UrmString(f"Undefined variable: {expr.name}"))
            return val
        elif isinstance(expr, ArrayLiteral):
            return UrmArray([self._eval_expr(e, env) for e in expr.elements])
        elif isinstance(expr, DictLiteral):
            pairs = {}
            for k, v in expr.pairs:
                key = self._expect_string(self._eval_expr(k, env))
                pairs[key] = self._eval_expr(v, env)
            return UrmDict(pairs)
        elif isinstance(expr, TupleLiteral):
            return UrmTuple(tuple(self._eval_expr(e, env) for e in expr.elements))
        elif isinstance(expr, PrefixExpr):
            return self._eval_prefix(expr, env)
        elif isinstance(expr, InfixExpr):
            return self._eval_infix(expr.operator, self._eval_expr(expr.left, env),
                                     self._eval_expr(expr.right, env))
        elif isinstance(expr, CallExpr):
            return self._eval_call(expr, env)
        elif isinstance(expr, IndexExpr):
            obj = self._eval_expr(expr.obj, env)
            idx = self._eval_expr(expr.index, env)
            return self._eval_index(obj, idx)
        elif isinstance(expr, SliceExpr):
            obj = self._eval_expr(expr.obj, env)
            start = int(self._to_number(self._eval_expr(expr.start, env))) if expr.start else 0
            end = int(self._to_number(self._eval_expr(expr.end, env))) if expr.end else None
            step = int(self._to_number(self._eval_expr(expr.step, env))) if expr.step else None
            if isinstance(obj, UrmArray):
                s = slice(start, end, step)
                return UrmArray(obj.elements[s])
            elif isinstance(obj, UrmString):
                s = slice(start, end, step)
                return UrmString(obj.value[s])
            return URM_NONE
        elif isinstance(expr, MemberExpr):
            obj = self._eval_expr(expr.obj, env)
            return self._eval_member(obj, expr.member, env)
        elif isinstance(expr, MethodCallExpr):
            obj = self._eval_expr(expr.obj, env)
            args = [self._eval_expr(a, env) for a in expr.arguments]
            return self._eval_method_call(obj, expr.method, args, env)
        elif isinstance(expr, LambdaExpr):
            return UrmFunction("<lambda>", expr.params, expr.body, env)
        elif isinstance(expr, SpawnExpr):
            return self._eval_spawn(expr, env)
        elif isinstance(expr, AwaitExpr):
            val = self._eval_expr(expr.expr, env)
            if isinstance(val, UrmFuture):
                return val.get_value()
            return val
        elif isinstance(expr, ChanExpr):
            cap = int(self._to_number(self._eval_expr(expr.capacity, env))) if expr.capacity else 0
            return UrmChannel(capacity=cap)
        elif isinstance(expr, IfExpr):
            return self._eval_if_expr(expr, env)
        elif isinstance(expr, MatchExpr):
            return self._eval_match_expr(expr, env)
        elif isinstance(expr, TypeCastExpr):
            val = self._eval_expr(expr.expr, env)
            target = expr.target_type.name
            if target in ("int", "i32", "i64"):
                return UrmInt(int(self._to_number(val)))
            elif target in ("float", "f32", "f64"):
                return UrmFloat(self._to_number(val))
            elif target == "string" or target == "str":
                return UrmString(self._value_to_display(val))
            elif target == "bool":
                return UrmBool(self._is_truthy(val))
            return val
        elif isinstance(expr, RangeExpr):
            start = int(self._to_number(self._eval_expr(expr.start, env)))
            end = int(self._to_number(self._eval_expr(expr.end, env)))
            return UrmArray([UrmInt(i) for i in range(start, end + (1 if expr.inclusive else 0))])
        return URM_NONE

    def _eval_prefix(self, expr: PrefixExpr, env: Environment) -> UrmValue:
        right = self._eval_expr(expr.right, env)
        if expr.operator == "!":
            return UrmBool(not self._is_truthy(right))
        elif expr.operator == "-":
            if isinstance(right, UrmInt):
                return UrmInt(-right.value)
            elif isinstance(right, UrmFloat):
                return UrmFloat(-right.value)
        elif expr.operator == "~":
            if isinstance(right, UrmInt):
                return UrmInt(~right.value)
        return URM_NONE

    def _eval_infix(self, op: str, left: UrmValue, right: UrmValue) -> UrmValue:
        # Arithmetic
        if op == "+":
            if isinstance(left, UrmString) or isinstance(right, UrmString):
                return UrmString(self._value_to_display(left) + self._value_to_display(right))
            if isinstance(left, UrmInt) and isinstance(right, UrmInt):
                return UrmInt(left.value + right.value)
            return UrmFloat(self._to_number(left) + self._to_number(right))
        elif op == "-":
            if isinstance(left, UrmInt) and isinstance(right, UrmInt):
                return UrmInt(left.value - right.value)
            return UrmFloat(self._to_number(left) - self._to_number(right))
        elif op == "*":
            if isinstance(left, UrmInt) and isinstance(right, UrmInt):
                return UrmInt(left.value * right.value)
            return UrmFloat(self._to_number(left) * self._to_number(right))
        elif op == "/":
            r = self._to_number(right)
            if r == 0:
                raise ThrowSignal(UrmString("Division by zero"))
            l = self._to_number(left)
            if isinstance(left, UrmInt) and isinstance(right, UrmInt) and l % r == 0:
                return UrmInt(int(l / r))
            return UrmFloat(l / r)
        elif op == "%":
            r = self._to_number(right)
            if r == 0:
                raise ThrowSignal(UrmString("Modulo by zero"))
            return UrmInt(int(self._to_number(left)) % int(r))
        elif op == "**":
            base = self._to_number(left)
            exp = self._to_number(right)
            result = math.pow(base, exp)
            if result == int(result) and isinstance(left, UrmInt) and isinstance(right, UrmInt):
                return UrmInt(int(result))
            return UrmFloat(result)
        # Comparison
        elif op == "==":
            return UrmBool(self._values_equal(left, right))
        elif op == "!=":
            return UrmBool(not self._values_equal(left, right))
        elif op == "<":
            return UrmBool(self._to_number(left) < self._to_number(right))
        elif op == ">":
            return UrmBool(self._to_number(left) > self._to_number(right))
        elif op == "<=":
            return UrmBool(self._to_number(left) <= self._to_number(right))
        elif op == ">=":
            return UrmBool(self._to_number(left) >= self._to_number(right))
        # Logical
        elif op == "&&":
            return UrmBool(self._is_truthy(left) and self._is_truthy(right))
        elif op == "||":
            return UrmBool(self._is_truthy(left) or self._is_truthy(right))
        # Bitwise
        elif op == "&":
            return UrmInt(int(self._to_number(left)) & int(self._to_number(right)))
        elif op == "|":
            return UrmInt(int(self._to_number(left)) | int(self._to_number(right)))
        elif op == "^":
            return UrmInt(int(self._to_number(left)) ^ int(self._to_number(right)))
        elif op == "<<":
            return UrmInt(int(self._to_number(left)) << int(self._to_number(right)))
        elif op == ">>":
            return UrmInt(int(self._to_number(left)) >> int(self._to_number(right)))
        return URM_NONE

    def _eval_call(self, expr: CallExpr, env: Environment) -> UrmValue:
        fn = self._eval_expr(expr.function, env)
        args = [self._eval_expr(a, env) for a in expr.arguments]
        return self._call_function(fn, args)

    def _eval_index(self, obj: UrmValue, idx: UrmValue) -> UrmValue:
        if isinstance(obj, UrmArray):
            i = int(self._to_number(idx))
            if 0 <= i < len(obj.elements):
                return obj.elements[i]
            elif i < 0 and abs(i) <= len(obj.elements):
                return obj.elements[i]
            raise ThrowSignal(UrmString(f"Index {i} out of range"))
        elif isinstance(obj, UrmDict):
            key = self._expect_string(idx)
            if key in obj.pairs:
                return obj.pairs[key]
            return URM_NONE
        elif isinstance(obj, UrmString):
            i = int(self._to_number(idx))
            if 0 <= i < len(obj.value):
                return UrmString(obj.value[i])
            raise ThrowSignal(UrmString(f"Index {i} out of range"))
        elif isinstance(obj, UrmTuple):
            i = int(self._to_number(idx))
            if 0 <= i < len(obj.elements):
                return obj.elements[i]
            raise ThrowSignal(UrmString(f"Index {i} out of range"))
        raise ThrowSignal(UrmString(f"Cannot index {type(obj).__name__}"))

    def _eval_member(self, obj: UrmValue, member: str, env: Environment) -> UrmValue:
        if isinstance(obj, UrmStruct):
            if member in obj.fields:
                return obj.fields[member]
            # Check impl methods
            if obj.name in self._impl_methods and member in self._impl_methods[obj.name]:
                method_decl = self._impl_methods[obj.name][member]
                fn = UrmFunction(method_decl.name, method_decl.params, method_decl.body, env)
                # Bind self
                bound_fn = UrmBuiltinFn(member, lambda *args, _fn=fn, _self=obj: self._call_function(
                    _fn, [_self] + list(args)))
                return bound_fn
            raise ThrowSignal(UrmString(f"Struct {obj.name} has no field '{member}'"))
        elif isinstance(obj, UrmDict):
            if member in obj.pairs:
                return obj.pairs[member]
            return URM_NONE
        elif isinstance(obj, UrmArray):
            # Built-in array methods
            if member == "length" or member == "len":
                return UrmInt(len(obj.elements))
            elif member == "push":
                return UrmBuiltinFn("push", lambda *a: (obj.elements.append(a[0]), obj)[1] if a else obj)
            elif member == "pop":
                return UrmBuiltinFn("pop", lambda: obj.elements.pop() if obj.elements else URM_NONE)
            elif member == "first":
                return obj.elements[0] if obj.elements else URM_NONE
            elif member == "last":
                return obj.elements[-1] if obj.elements else URM_NONE
            elif member == "is_empty":
                return UrmBool(len(obj.elements) == 0)
        elif isinstance(obj, UrmString):
            # Built-in string methods
            if member == "length" or member == "len":
                return UrmInt(len(obj.value))
            elif member == "is_empty":
                return UrmBool(len(obj.value) == 0)
            elif member == "upper":
                return UrmString(obj.value.upper())
            elif member == "lower":
                return UrmString(obj.value.lower())
            elif member == "trim":
                return UrmString(obj.value.strip())
            elif member == "split":
                return UrmBuiltinFn("split", lambda *a: UrmArray([UrmString(p) for p in obj.value.split(self._expect_string(a[0]) if a else " ")]))
        elif isinstance(obj, UrmEnumVariant):
            if member == "name":
                return UrmString(obj.variant_name)
            elif member == "fields":
                return UrmArray(obj.fields)
            elif obj.fields and member.startswith("_") and member[1:].isdigit():
                idx = int(member[1:])
                return obj.fields[idx] if idx < len(obj.fields) else URM_NONE
        elif isinstance(obj, UrmFuture):
            if member == "get_value" or member == "get" or member == "await":
                return UrmBuiltinFn("get_value", lambda *a: obj.get_value(timeout=self._to_number(a[0]) if a else 30.0))
            elif member == "is_ready" or member == "is_done":
                return UrmBool(obj.result_event.is_set())
            elif member == "value":
                if obj.result_event.is_set():
                    return obj._value if obj._value is not None else URM_NONE
                return URM_NONE
        elif isinstance(obj, UrmChannel):
            if member == "send":
                return UrmBuiltinFn("send", lambda *a: (obj.send(a[0]), URM_NONE)[1] if a else URM_NONE)
            elif member == "receive" or member == "recv":
                return UrmBuiltinFn("receive", lambda: obj.receive())
            elif member == "close":
                obj._closed = True
                return URM_NONE
            elif member == "is_closed":
                return UrmBool(obj._closed)
            elif member == "capacity":
                return UrmInt(obj.capacity)
        raise ThrowSignal(UrmString(f"Cannot access member '{member}' on {type(obj).__name__}"))

    def _eval_method_call(self, obj: UrmValue, method: str, args: list[UrmValue], env: Environment) -> UrmValue:
        if isinstance(obj, UrmStruct):
            if obj.name in self._impl_methods and method in self._impl_methods[obj.name]:
                method_decl = self._impl_methods[obj.name][method]
                fn = UrmFunction(method_decl.name, method_decl.params, method_decl.body, env)
                return self._call_function(fn, [obj] + args)
            raise ThrowSignal(UrmString(f"Struct {obj.name} has no method '{method}'"))
        # For other types, try member access (might be a function)
        member = self._eval_member(obj, method, env)
        if isinstance(member, (UrmFunction, UrmBuiltinFn)):
            return self._call_function(member, args)
        return member

    def _eval_spawn(self, expr: SpawnExpr, env: Environment) -> UrmValue:
        event = threading.Event()
        future = UrmFuture(event)
        call_expr = expr.call

        def run():
            try:
                fn = self._eval_expr(call_expr.function, env)
                args = [self._eval_expr(a, env) for a in call_expr.arguments]
                result = self._call_function(fn, args)
                future.set_value(result)
            except ThrowSignal as e:
                future.set_value(e.value)
            except Exception as e:
                future.set_value(UrmString(str(e)))

        t = threading.Thread(target=run, daemon=True)
        t.start()
        return future

    def _eval_if(self, stmt: IfStmt, env: Environment) -> UrmValue:
        condition = self._eval_expr(stmt.condition, env)
        if self._is_truthy(condition):
            return self._eval_block(stmt.consequence, Environment(parent=env))
        for elif_cond, elif_body in stmt.elif_clauses:
            if self._is_truthy(self._eval_expr(elif_cond, env)):
                return self._eval_block(elif_body, Environment(parent=env))
        if stmt.alternative:
            return self._eval_block(stmt.alternative, Environment(parent=env))
        return URM_NONE

    def _eval_if_expr(self, expr: IfExpr, env: Environment) -> UrmValue:
        condition = self._eval_expr(expr.condition, env)
        if self._is_truthy(condition):
            return self._eval_block(expr.consequence, Environment(parent=env))
        for elif_cond, elif_body in expr.elif_clauses:
            if self._is_truthy(self._eval_expr(elif_cond, env)):
                return self._eval_block(elif_body, Environment(parent=env))
        if expr.alternative:
            return self._eval_block(expr.alternative, Environment(parent=env))
        return URM_NONE

    def _eval_while(self, stmt: WhileStmt, env: Environment) -> UrmValue:
        result = URM_NONE
        while self._is_truthy(self._eval_expr(stmt.condition, env)):
            try:
                result = self._eval_block(stmt.body, Environment(parent=env))
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return result

    def _eval_for_in(self, stmt: ForInStmt, env: Environment) -> UrmValue:
        result = URM_NONE
        iterable = self._eval_expr(stmt.iterable, env)
        items = []
        if isinstance(iterable, UrmArray):
            items = iterable.elements
        elif isinstance(iterable, UrmString):
            items = [UrmString(c) for c in iterable.value]
        for item in items:
            loop_env = Environment(parent=env)
            loop_env.define(stmt.name, item, mutable=True)
            try:
                result = self._eval_block(stmt.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return result

    def _eval_for(self, stmt: ForStmt, env: Environment) -> UrmValue:
        loop_env = Environment(parent=env)
        if stmt.init:
            self._eval_statement(stmt.init, loop_env)
        result = URM_NONE
        while True:
            if stmt.condition:
                cond = self._eval_expr(stmt.condition, loop_env)
                if not self._is_truthy(cond):
                    break
            try:
                result = self._eval_block(stmt.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                pass
            if stmt.update:
                self._eval_expr(stmt.update, loop_env)
        return result

    def _eval_match(self, stmt: MatchStmt, env: Environment) -> UrmValue:
        subject = self._eval_expr(stmt.subject, env)
        for arm in stmt.arms:
            # Handle wildcard pattern (_)
            if isinstance(arm.pattern, Identifier) and arm.pattern.name == "_":
                if arm.guard:
                    guard_val = self._eval_expr(arm.guard, env)
                    if not self._is_truthy(guard_val):
                        continue
                return self._eval_block(arm.body, Environment(parent=env))
            pattern_val = self._eval_expr(arm.pattern, env)
            if self._values_equal(subject, pattern_val):
                if arm.guard:
                    guard_val = self._eval_expr(arm.guard, env)
                    if not self._is_truthy(guard_val):
                        continue
                return self._eval_block(arm.body, Environment(parent=env))
        return URM_NONE

    def _eval_match_expr(self, expr: MatchExpr, env: Environment) -> UrmValue:
        return self._eval_match(MatchStmt(subject=expr.subject, arms=expr.arms), env)

    def _eval_try_catch(self, stmt: TryCatchStmt, env: Environment) -> UrmValue:
        result = URM_NONE
        try:
            result = self._eval_block(stmt.try_block, Environment(parent=env))
        except ThrowSignal as e:
            if stmt.catch_block:
                catch_env = Environment(parent=env)
                if stmt.catch_var:
                    catch_env.define(stmt.catch_var, e.value, mutable=True)
                result = self._eval_block(stmt.catch_block, catch_env)
            else:
                raise
        finally:
            if stmt.finally_block:
                self._eval_block(stmt.finally_block, Environment(parent=env))
        return result

    def _eval_block(self, block: Block, env: Environment) -> UrmValue:
        result = URM_NONE
        for stmt in block.statements:
            result = self._eval_statement(stmt, env)
        return result
