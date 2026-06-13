"""
Urmom Lang Object Model
=======================
The native object system for Urmom Lang runtime.
Every value in Urmom Lang is a UrmObject - this is the language's
OWN type hierarchy, not borrowed from any other language.

Type System:
  int, float, string, bool, none, array, dict, tuple, set, range,
  function, builtin, struct, struct_instance, enum, enum_variant,
  channel, future, generator, module, trait, error, bytes, regex, type
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Callable, List, Dict, Set, Tuple
from enum import Enum
import queue
import threading
import re


class UrmType(Enum):
    """All native types in Urmom Lang."""
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    NONE = "none"
    ARRAY = "array"
    DICT = "dict"
    TUPLE = "tuple"
    SET = "set"
    RANGE = "range"
    FUNCTION = "function"
    BUILTIN = "builtin"
    STRUCT = "struct"
    STRUCT_INSTANCE = "struct_instance"
    ENUM = "enum"
    ENUM_VARIANT = "enum_variant"
    CHANNEL = "channel"
    FUTURE = "future"
    GENERATOR = "generator"
    MODULE = "module"
    TRAIT = "trait"
    IMPL = "impl"
    ERROR = "error"
    BYTES = "bytes"
    REGEX = "regex"
    TYPE = "type"
    ITERATOR = "iterator"
    MUTEX = "mutex"
    ANY = "any"


# ═══════════════════════════════════════════════════════════════
# Base Object
# ═══════════════════════════════════════════════════════════════

class UrmObject:
    """Base class for ALL Urmom Lang runtime values."""
    
    def __init__(self):
        self.type = UrmType.ANY
    
    def is_truthy(self) -> bool:
        return True
    
    def urm_repr(self) -> str:
        return str(self)
    
    def urm_type_name(self) -> str:
        return self.type.value
    
    def urm_hash(self) -> int:
        return id(self)
    
    def urm_eq(self, other) -> bool:
        return self is other
    
    def urm_clone(self) -> 'UrmObject':
        import copy
        return copy.deepcopy(self)


# ═══════════════════════════════════════════════════════════════
# Primitive Types
# ═══════════════════════════════════════════════════════════════

@dataclass
class UrmInt(UrmObject):
    """Urmom Lang integer - arbitrary precision."""
    value: int = 0
    
    def __post_init__(self):
        self.type = UrmType.INT
        UrmObject.__init__(self)
        super().__init__()
    
    def is_truthy(self) -> bool:
        return self.value != 0
    
    def urm_repr(self) -> str:
        return str(self.value)
    
    def urm_hash(self) -> int:
        return hash(self.value)
    
    def urm_eq(self, other) -> bool:
        return isinstance(other, UrmInt) and self.value == other.value
    
    def __add__(self, other):
        if isinstance(other, UrmInt): return UrmInt(self.value + other.value)
        if isinstance(other, UrmFloat): return UrmFloat(self.value + other.value)
        return NotImplemented
    
    def __sub__(self, other):
        if isinstance(other, UrmInt): return UrmInt(self.value - other.value)
        if isinstance(other, UrmFloat): return UrmFloat(self.value - other.value)
        return NotImplemented
    
    def __mul__(self, other):
        if isinstance(other, UrmInt): return UrmInt(self.value * other.value)
        if isinstance(other, UrmFloat): return UrmFloat(self.value * other.value)
        return NotImplemented
    
    def __floordiv__(self, other):
        if isinstance(other, UrmInt) and other.value != 0:
            return UrmInt(self.value // other.value)
        return NotImplemented
    
    def __mod__(self, other):
        if isinstance(other, UrmInt) and other.value != 0:
            return UrmInt(self.value % other.value)
        return NotImplemented
    
    def __pow__(self, other):
        if isinstance(other, UrmInt): return UrmInt(self.value ** other.value)
        return NotImplemented
    
    def __neg__(self):
        return UrmInt(-self.value)
    
    def __and__(self, other):
        if isinstance(other, UrmInt): return UrmInt(self.value & other.value)
        return NotImplemented
    
    def __or__(self, other):
        if isinstance(other, UrmInt): return UrmInt(self.value | other.value)
        return NotImplemented
    
    def __xor__(self, other):
        if isinstance(other, UrmInt): return UrmInt(self.value ^ other.value)
        return NotImplemented
    
    def __lshift__(self, other):
        if isinstance(other, UrmInt): return UrmInt(self.value << other.value)
        return NotImplemented
    
    def __rshift__(self, other):
        if isinstance(other, UrmInt): return UrmInt(self.value >> other.value)
        return NotImplemented


@dataclass
class UrmFloat(UrmObject):
    """Urmom Lang floating point number."""
    value: float = 0.0
    
    def __post_init__(self):
        self.type = UrmType.FLOAT
        UrmObject.__init__(self)
    
    def is_truthy(self) -> bool:
        return self.value != 0.0
    
    def urm_repr(self) -> str:
        if self.value == int(self.value) and not (self.value != self.value):
            return f"{self.value:.1f}"
        return str(self.value)
    
    def urm_hash(self) -> int:
        return hash(self.value)
    
    def urm_eq(self, other) -> bool:
        if isinstance(other, UrmFloat): return self.value == other.value
        if isinstance(other, UrmInt): return self.value == other.value
        return False
    
    def __add__(self, other):
        if isinstance(other, (UrmFloat, UrmInt)):
            return UrmFloat(self.value + other.value)
        return NotImplemented
    
    def __sub__(self, other):
        if isinstance(other, (UrmFloat, UrmInt)):
            return UrmFloat(self.value - other.value)
        return NotImplemented
    
    def __mul__(self, other):
        if isinstance(other, (UrmFloat, UrmInt)):
            return UrmFloat(self.value * other.value)
        return NotImplemented
    
    def __truediv__(self, other):
        if isinstance(other, (UrmFloat, UrmInt)) and other.value != 0:
            return UrmFloat(self.value / other.value)
        return NotImplemented
    
    def __neg__(self):
        return UrmFloat(-self.value)


@dataclass
class UrmString(UrmObject):
    """Urmom Lang string - UTF-8 encoded, immutable."""
    value: str = ""
    
    def __post_init__(self):
        self.type = UrmType.STRING
        UrmObject.__init__(self)
    
    def is_truthy(self) -> bool:
        return len(self.value) > 0
    
    def urm_repr(self) -> str:
        return self.value
    
    def urm_hash(self) -> int:
        return hash(self.value)
    
    def urm_eq(self, other) -> bool:
        return isinstance(other, UrmString) and self.value == other.value
    
    def __add__(self, other):
        if isinstance(other, UrmString):
            return UrmString(self.value + other.value)
        return NotImplemented
    
    def __len__(self):
        return len(self.value)


@dataclass
class UrmBool(UrmObject):
    """Urmom Lang boolean."""
    value: bool = False
    
    def __post_init__(self):
        self.type = UrmType.BOOL
        UrmObject.__init__(self)
    
    def is_truthy(self) -> bool:
        return self.value
    
    def urm_repr(self) -> str:
        return "true" if self.value else "false"
    
    def urm_hash(self) -> int:
        return hash(self.value)
    
    def urm_eq(self, other) -> bool:
        return isinstance(other, UrmBool) and self.value == other.value


@dataclass
class UrmNone(UrmObject):
    """Urmom Lang null value - represents absence of value."""
    
    def __post_init__(self):
        self.type = UrmType.NONE
        UrmObject.__init__(self)
    
    def is_truthy(self) -> bool:
        return False
    
    def urm_repr(self) -> str:
        return "none"
    
    def urm_hash(self) -> int:
        return hash(None)
    
    def urm_eq(self, other) -> bool:
        return isinstance(other, UrmNone)


# Singleton for none
URM_NONE = UrmNone()
URM_TRUE = UrmBool(True)
URM_FALSE = UrmBool(False)


# ═══════════════════════════════════════════════════════════════
# Collection Types
# ═══════════════════════════════════════════════════════════════

@dataclass
class UrmArray(UrmObject):
    """Urmom Lang dynamic array (list)."""
    elements: list = field(default_factory=list)
    
    def __post_init__(self):
        self.type = UrmType.ARRAY
        UrmObject.__init__(self)
    
    def is_truthy(self) -> bool:
        return len(self.elements) > 0
    
    def urm_repr(self) -> str:
        items = ", ".join(_repr(e) for e in self.elements)
        return f"[{items}]"
    
    def urm_eq(self, other) -> bool:
        if not isinstance(other, UrmArray): return False
        if len(self.elements) != len(other.elements): return False
        return all(_eq(a, b) for a, b in zip(self.elements, other.elements))
    
    def append(self, val):
        self.elements.append(val)
    
    def extend(self, vals):
        self.elements.extend(vals)
    
    def get(self, index):
        if isinstance(index, UrmInt):
            idx = index.value
            if -len(self.elements) <= idx < len(self.elements):
                return self.elements[idx]
        raise UrmRuntimeError(f"Index out of bounds: {_repr(index)}")
    
    def set(self, index, value):
        if isinstance(index, UrmInt):
            idx = index.value
            if 0 <= idx < len(self.elements):
                self.elements[idx] = value
                return
        raise UrmRuntimeError(f"Index out of bounds: {_repr(index)}")
    
    def length(self) -> int:
        return len(self.elements)
    
    def map(self, fn):
        result = []
        for e in self.elements:
            result.append(_call_fn(fn, [e]))
        return UrmArray(result)
    
    def filter(self, fn):
        result = []
        for e in self.elements:
            if _is_truthy(_call_fn(fn, [e])):
                result.append(e)
        return UrmArray(result)
    
    def reduce(self, fn, init=None):
        acc = init if init is not None else self.elements[0]
        start = 0 if init is not None else 1
        for e in self.elements[start:]:
            acc = _call_fn(fn, [acc, e])
        return acc
    
    def sort(self, fn=None):
        if fn:
            self.elements.sort(key=lambda x: _call_fn(fn, [x]).value 
                             if hasattr(_call_fn(fn, [x]), 'value') else 0)
        else:
            self.elements.sort(key=lambda x: x.value if hasattr(x, 'value') else str(x))
    
    def reverse(self):
        self.elements.reverse()
    
    def slice(self, start, end=None):
        s = start.value if isinstance(start, UrmInt) else 0
        e = end.value if isinstance(end, UrmInt) else len(self.elements)
        return UrmArray(self.elements[s:e])
    
    def find(self, fn):
        for e in self.elements:
            if _is_truthy(_call_fn(fn, [e])):
                return e
        return URM_NONE
    
    def find_index(self, fn):
        for i, e in enumerate(self.elements):
            if _is_truthy(_call_fn(fn, [e])):
                return UrmInt(i)
        return URM_NONE
    
    def contains(self, val):
        for e in self.elements:
            if _eq(e, val):
                return URM_TRUE
        return URM_FALSE
    
    def flat(self, depth=1):
        result = []
        def _flat(arr, d):
            for e in arr:
                if isinstance(e, UrmArray) and d > 0:
                    _flat(e.elements, d - 1)
                else:
                    result.append(e)
        _flat(self.elements, depth)
        return UrmArray(result)
    
    def unique(self):
        seen = []
        result = []
        for e in self.elements:
            key = _hash(e)
            if key not in seen:
                seen.append(key)
                result.append(e)
        return UrmArray(result)
    
    def zip_with(self, other):
        if not isinstance(other, UrmArray): return UrmArray()
        result = []
        for a, b in zip(self.elements, other.elements):
            result.append(UrmArray([a, b]))
        return UrmArray(result)
    
    def chunk(self, size):
        s = size.value if isinstance(size, UrmInt) else 1
        result = []
        for i in range(0, len(self.elements), s):
            result.append(UrmArray(self.elements[i:i+s]))
        return UrmArray(result)


@dataclass
class UrmDict(UrmObject):
    """Urmom Lang dictionary (hash map)."""
    pairs: dict = field(default_factory=dict)
    
    def __post_init__(self):
        self.type = UrmType.DICT
        UrmObject.__init__(self)
    
    def is_truthy(self) -> bool:
        return len(self.pairs) > 0
    
    def urm_repr(self) -> str:
        items = ", ".join(f"{k}: {_repr(v)}" for k, v in self.pairs.items())
        return "{" + items + "}"
    
    def get(self, key):
        k = _to_hash_key(key)
        if k in self.pairs:
            return self.pairs[k]
        return URM_NONE
    
    def set(self, key, value):
        k = _to_hash_key(key)
        self.pairs[k] = value
    
    def has(self, key) -> bool:
        k = _to_hash_key(key)
        return k in self.pairs
    
    def remove(self, key):
        k = _to_hash_key(key)
        if k in self.pairs:
            del self.pairs[k]
    
    def keys(self):
        return UrmArray([_from_hash_key(k) for k in self.pairs.keys()])
    
    def values(self):
        return UrmArray(list(self.pairs.values()))
    
    def items(self):
        result = []
        for k, v in self.pairs.items():
            result.append(UrmArray([_from_hash_key(k), v]))
        return UrmArray(result)
    
    def length(self) -> int:
        return len(self.pairs)
    
    def merge(self, other):
        if isinstance(other, UrmDict):
            result = UrmDict(dict(self.pairs))
            result.pairs.update(other.pairs)
            return result
        return self


@dataclass
class UrmTuple(UrmObject):
    """Urmom Lang tuple - immutable ordered collection."""
    elements: list = field(default_factory=list)
    
    def __post_init__(self):
        self.type = UrmType.TUPLE
        UrmObject.__init__(self)
    
    def is_truthy(self) -> bool:
        return len(self.elements) > 0
    
    def urm_repr(self) -> str:
        items = ", ".join(_repr(e) for e in self.elements)
        if len(self.elements) == 1:
            return f"({items},)"
        return f"({items})"
    
    def get(self, index):
        if isinstance(index, UrmInt):
            idx = index.value
            if -len(self.elements) <= idx < len(self.elements):
                return self.elements[idx]
        raise UrmRuntimeError(f"Index out of bounds: {_repr(index)}")
    
    def length(self) -> int:
        return len(self.elements)


@dataclass
class UrmSet(UrmObject):
    """Urmom Lang set - unique unordered collection."""
    elements: set = field(default_factory=set)
    
    def __post_init__(self):
        self.type = UrmType.SET
        UrmObject.__init__(self)
    
    def is_truthy(self) -> bool:
        return len(self.elements) > 0
    
    def urm_repr(self) -> str:
        items = ", ".join(str(e) for e in self.elements)
        return f"{{{items}}}"
    
    def add(self, val):
        self.elements.add(_to_hash_key(val))
    
    def has(self, val) -> bool:
        return _to_hash_key(val) in self.elements
    
    def remove(self, val):
        self.elements.discard(_to_hash_key(val))
    
    def union(self, other):
        if isinstance(other, UrmSet):
            return UrmSet(self.elements | other.elements)
        return self
    
    def intersection(self, other):
        if isinstance(other, UrmSet):
            return UrmSet(self.elements & other.elements)
        return UrmSet()
    
    def difference(self, other):
        if isinstance(other, UrmSet):
            return UrmSet(self.elements - other.elements)
        return self


@dataclass
class UrmRange(UrmObject):
    """Urmom Lang range - lazy integer sequence."""
    start: int = 0
    end: int = 0
    step: int = 1
    inclusive: bool = False
    
    def __post_init__(self):
        self.type = UrmType.RANGE
        UrmObject.__init__(self)
    
    def is_truthy(self) -> bool:
        if self.step > 0:
            end = self.end + 1 if self.inclusive else self.end
            return self.start < end
        end = self.end - 1 if self.inclusive else self.end
        return self.start > end
    
    def to_list(self) -> list:
        end = self.end + 1 if self.inclusive else self.end
        if self.step == 0:
            return []
        return list(range(self.start, end, self.step))
    
    def to_array(self) -> 'UrmArray':
        return UrmArray([UrmInt(v) for v in self.to_list()])
    
    def urm_repr(self) -> str:
        op = ".." if self.inclusive else "..<"
        step = f":{self.step}" if self.step != 1 else ""
        return f"{self.start}{op}{self.end}{step}"
    
    def length(self) -> int:
        if self.step == 0: return 0
        end = self.end + 1 if self.inclusive else self.end
        if self.step > 0:
            return max(0, (end - self.start + self.step - 1) // self.step)
        return max(0, (self.start - end - self.step - 1) // (-self.step))


# ═══════════════════════════════════════════════════════════════
# Function Types
# ═══════════════════════════════════════════════════════════════

@dataclass
class UrmFunction(UrmObject):
    """Urmom Lang user-defined function."""
    name: str = ""
    chunk_index: int = 0
    arity: int = 0
    upvalues: list = field(default_factory=list)
    defaults: list = field(default_factory=list)
    is_variadic: bool = False
    is_method: bool = False
    is_static: bool = False
    is_async: bool = False
    is_generator: bool = False
    param_names: list = field(default_factory=list)
    closure_env: Any = None  # Reference to enclosing environment
    
    def __post_init__(self):
        self.type = UrmType.FUNCTION
        UrmObject.__init__(self)
    
    def urm_repr(self) -> str:
        prefix = ""
        if self.is_async: prefix = "async "
        if self.is_generator: prefix = "gen "
        return f"<{prefix}fn {self.name}/{self.arity}>"


@dataclass
class UrmBuiltinFn(UrmObject):
    """Urmom Lang built-in function (implemented in the runtime)."""
    name: str = ""
    fn: Any = None
    arity: int = -1  # -1 = variadic
    
    def __post_init__(self):
        self.type = UrmType.BUILTIN
        UrmObject.__init__(self)
    
    def urm_repr(self) -> str:
        return f"<builtin {self.name}>"


# ═══════════════════════════════════════════════════════════════
# Struct / Enum / Trait Types
# ═══════════════════════════════════════════════════════════════

@dataclass
class UrmStructDef(UrmObject):
    """Urmom Lang struct type definition."""
    name: str = ""
    fields: list = field(default_factory=list)
    methods: dict = field(default_factory=dict)
    static_methods: dict = field(default_factory=dict)
    traits: list = field(default_factory=list)
    field_types: dict = field(default_factory=dict)  # field -> type_name
    field_defaults: dict = field(default_factory=dict)
    
    def __post_init__(self):
        self.type = UrmType.STRUCT
        UrmObject.__init__(self)
    
    def urm_repr(self) -> str:
        return f"<struct {self.name}>"


@dataclass
class UrmStructInstance(UrmObject):
    """Urmom Lang struct instance."""
    struct_def: Any = None
    fields: dict = field(default_factory=dict)
    
    def __post_init__(self):
        self.type = UrmType.STRUCT
        UrmObject.__init__(self)
    
    def urm_repr(self) -> str:
        if self.struct_def:
            items = ", ".join(f"{k}: {_repr(v)}" for k, v in self.fields.items())
            return f"{self.struct_def.name}({items})"
        return "<struct instance>"
    
    def get_field(self, name: str):
        if name in self.fields:
            return self.fields[name]
        return URM_NONE
    
    def set_field(self, name: str, value):
        self.fields[name] = value


@dataclass
class UrmEnumDef(UrmObject):
    """Urmom Lang enum type definition."""
    name: str = ""
    variants: dict = field(default_factory=dict)  # name -> [field_types] or None
    methods: dict = field(default_factory=dict)
    
    def __post_init__(self):
        self.type = UrmType.ENUM
        UrmObject.__init__(self)
    
    def urm_repr(self) -> str:
        return f"<enum {self.name}>"


@dataclass
class UrmEnumVariant(UrmObject):
    """Urmom Lang enum variant instance."""
    enum_name: str = ""
    variant_name: str = ""
    data: list = field(default_factory=list)
    
    def __post_init__(self):
        self.type = UrmType.ENUM
        UrmObject.__init__(self)
    
    def urm_repr(self) -> str:
        if self.data:
            items = ", ".join(_repr(e) for e in self.data)
            return f"{self.enum_name}::{self.variant_name}({items})"
        return f"{self.enum_name}::{self.variant_name}"
    
    def urm_eq(self, other) -> bool:
        if not isinstance(other, UrmEnumVariant): return False
        return (self.enum_name == other.enum_name and 
                self.variant_name == other.variant_name and
                len(self.data) == len(other.data) and
                all(_eq(a, b) for a, b in zip(self.data, other.data)))


@dataclass
class UrmTraitDef(UrmObject):
    """Urmom Lang trait definition."""
    name: str = ""
    method_signatures: list = field(default_factory=list)
    default_methods: dict = field(default_factory=dict)
    
    def __post_init__(self):
        self.type = UrmType.TRAIT
        UrmObject.__init__(self)
    
    def urm_repr(self) -> str:
        return f"<trait {self.name}>"


# ═══════════════════════════════════════════════════════════════
# Concurrency Types
# ═══════════════════════════════════════════════════════════════

@dataclass
class UrmChannel(UrmObject):
    """Urmom Lang channel for concurrent communication."""
    capacity: int = 0
    _queue: Any = None
    _closed: bool = False
    
    def __post_init__(self):
        self.type = UrmType.CHANNEL
        UrmObject.__init__(self)
        self._queue = queue.Queue(maxsize=self.capacity if self.capacity > 0 else 0)
    
    def send(self, value):
        if self._closed:
            raise UrmRuntimeError("Cannot send to closed channel")
        self._queue.put(value, timeout=5.0)
    
    def receive(self, timeout=None):
        try:
            return self._queue.get(timeout=timeout or 5.0)
        except queue.Empty:
            return URM_NONE
    
    def try_receive(self):
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return URM_NONE
    
    def close(self):
        self._closed = True
    
    def is_closed(self) -> bool:
        return self._closed
    
    def urm_repr(self) -> str:
        return f"<channel cap={self.capacity} closed={self._closed}>"


@dataclass
class UrmFuture(UrmObject):
    """Urmom Lang future - represents an async computation."""
    _result: Any = None
    _ready: Any = None
    _thread: Any = None
    _error: Any = None
    
    def __post_init__(self):
        self.type = UrmType.FUTURE
        UrmObject.__init__(self)
        self._ready = threading.Event()
    
    def set_result(self, value):
        self._result = value
        self._ready.set()
    
    def set_error(self, err):
        self._error = err
        self._ready.set()
    
    def get_value(self, timeout=None):
        self._ready.wait(timeout=timeout)
        if self._error:
            raise self._error
        return self._result
    
    def is_ready(self) -> bool:
        return self._ready.is_set()
    
    def urm_repr(self) -> str:
        state = "ready" if self.is_ready() else "pending"
        return f"<future {state}>"


@dataclass
class UrmMutex(UrmObject):
    """Urmom Lang mutex for synchronization."""
    _lock: Any = None
    
    def __post_init__(self):
        self.type = UrmType.MUTEX
        UrmObject.__init__(self)
        self._lock = threading.Lock()
    
    def acquire(self):
        self._lock.acquire()
    
    def release(self):
        self._lock.release()
    
    def urm_repr(self) -> str:
        return "<mutex>"


# ═══════════════════════════════════════════════════════════════
# Generator / Iterator
# ═══════════════════════════════════════════════════════════════

@dataclass
class UrmGenerator(UrmObject):
    """Urmom Lang generator - lazy sequence producer."""
    name: str = ""
    _iterator: Any = None
    _exhausted: bool = False
    
    def __post_init__(self):
        self.type = UrmType.GENERATOR
        UrmObject.__init__(self)
    
    def urm_repr(self) -> str:
        return f"<generator {self.name}>"


@dataclass
class UrmIterator(UrmObject):
    """Urmom Lang iterator wrapper."""
    _source: Any = None
    _index: int = 0
    
    def __post_init__(self):
        self.type = UrmType.ITERATOR
        UrmObject.__init__(self)
    
    def next(self):
        if isinstance(self._source, UrmArray):
            if self._index < len(self._source.elements):
                val = self._source.elements[self._index]
                self._index += 1
                return val
        elif isinstance(self._source, UrmRange):
            items = self._source.to_list()
            if self._index < len(items):
                val = UrmInt(items[self._index])
                self._index += 1
                return val
        elif isinstance(self._source, UrmDict):
            keys = list(self._source.pairs.keys())
            if self._index < len(keys):
                val = _from_hash_key(keys[self._index])
                self._index += 1
                return val
        elif isinstance(self._source, UrmString):
            if self._index < len(self._source.value):
                val = UrmString(self._source.value[self._index])
                self._index += 1
                return val
        return URM_NONE
    
    def has_next(self) -> bool:
        if isinstance(self._source, UrmArray):
            return self._index < len(self._source.elements)
        elif isinstance(self._source, UrmRange):
            items = self._source.to_list()
            return self._index < len(items)
        elif isinstance(self._source, UrmDict):
            return self._index < len(self._source.pairs)
        elif isinstance(self._source, UrmString):
            return self._index < len(self._source.value)
        return False
    
    def urm_repr(self) -> str:
        return f"<iterator at {self._index}>"


# ═══════════════════════════════════════════════════════════════
# Module / Error / Utility Types
# ═══════════════════════════════════════════════════════════════

@dataclass
class UrmModule(UrmObject):
    """Urmom Lang module - a namespace of exports."""
    name: str = ""
    exports: dict = field(default_factory=dict)
    
    def __post_init__(self):
        self.type = UrmType.MODULE
        UrmObject.__init__(self)
    
    def urm_repr(self) -> str:
        return f"<module {self.name}>"


@dataclass
class UrmError(UrmObject):
    """Urmom Lang error value."""
    error_type: str = "Error"
    message: str = ""
    traceback: list = field(default_factory=list)
    code: int = 1
    
    def __post_init__(self):
        self.type = UrmType.ERROR
        UrmObject.__init__(self)
    
    def is_truthy(self) -> bool:
        return True
    
    def urm_repr(self) -> str:
        return f"{self.error_type}: {self.message}"


@dataclass
class UrmBytes(UrmObject):
    """Urmom Lang bytes object."""
    data: bytes = b""
    
    def __post_init__(self):
        self.type = UrmType.BYTES
        UrmObject.__init__(self)
    
    def urm_repr(self) -> str:
        return f"<bytes {len(self.data)}>"
    
    def length(self) -> int:
        return len(self.data)


@dataclass
class UrmRegex(UrmObject):
    """Urmom Lang compiled regex."""
    pattern: str = ""
    _compiled: Any = None
    flags: int = 0
    
    def __post_init__(self):
        self.type = UrmType.REGEX
        UrmObject.__init__(self)
        self._compiled = re.compile(self.pattern, self.flags)
    
    def urm_repr(self) -> str:
        return f"<regex /{self.pattern}/>"
    
    def match(self, text):
        m = self._compiled.match(text)
        return m
    
    def search(self, text):
        return self._compiled.search(text)
    
    def find_all(self, text):
        return self._compiled.findall(text)
    
    def replace(self, text, replacement):
        return self._compiled.sub(replacement, text)
    
    def split(self, text):
        return self._compiled.split(text)


@dataclass
class UrmTypeObj(UrmObject):
    """Urmom Lang type descriptor."""
    type_name: str = ""
    type_def: Any = None
    
    def __post_init__(self):
        self.type = UrmType.TYPE
        UrmObject.__init__(self)
    
    def urm_repr(self) -> str:
        return f"<type {self.type_name}>"


# ═══════════════════════════════════════════════════════════════
# Runtime Error
# ═══════════════════════════════════════════════════════════════

class UrmRuntimeError(Exception):
    """Error raised during Urmom Lang execution."""
    def __init__(self, message: str, error_type: str = "RuntimeError"):
        super().__init__(message)
        self.error_type = error_type
        self.message = message


class UrmCompileError(Exception):
    """Error raised during Urmom Lang compilation."""
    def __init__(self, message: str, line: int = 0, col: int = 0):
        super().__init__(message)
        self.line = line
        self.col = col


# ═══════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════

def _repr(obj) -> str:
    """Get Urmom Lang string representation."""
    if isinstance(obj, UrmObject):
        return obj.urm_repr()
    return str(obj)


def _eq(a, b) -> bool:
    """Check Urmom Lang equality."""
    if isinstance(a, UrmObject) and isinstance(b, UrmObject):
        return a.urm_eq(b)
    return a == b


def _hash(obj) -> int:
    """Get hash of Urmom Lang object."""
    if isinstance(obj, UrmObject):
        return obj.urm_hash()
    return hash(obj)


def _is_truthy(obj) -> bool:
    """Check Urmom Lang truthiness."""
    if isinstance(obj, UrmObject):
        return obj.is_truthy()
    return bool(obj)


def _to_hash_key(obj) -> str:
    """Convert a UrmObject to a hashable key for dicts/sets."""
    if isinstance(obj, UrmString):
        return f"s:{obj.value}"
    if isinstance(obj, UrmInt):
        return f"i:{obj.value}"
    if isinstance(obj, UrmFloat):
        return f"f:{obj.value}"
    if isinstance(obj, UrmBool):
        return f"b:{obj.value}"
    if isinstance(obj, UrmNone):
        return "n:"
    return f"o:{id(obj)}"


def _from_hash_key(key: str):
    """Convert a hash key back to a UrmObject."""
    if key.startswith("s:"):
        return UrmString(key[2:])
    if key.startswith("i:"):
        return UrmInt(int(key[2:]))
    if key.startswith("f:"):
        return UrmFloat(float(key[2:]))
    if key.startswith("b:"):
        return URM_TRUE if key[2:] == "True" else URM_FALSE
    if key.startswith("n:"):
        return URM_NONE
    return URM_NONE


def _call_fn(fn, args):
    """Call a Urmom Lang function - used by object methods."""
    if isinstance(fn, UrmBuiltinFn):
        return fn.fn(*args)
    # For UrmFunction, the VM will handle the actual call
    # This is a fallback for built-in method operations
    if callable(getattr(fn, 'fn', None)):
        return fn.fn(*args)
    raise UrmRuntimeError(f"Cannot call {_repr(fn)}")


def _to_urm_value(python_val) -> UrmObject:
    """Convert a Python value to a UrmObject."""
    if python_val is None:
        return URM_NONE
    if isinstance(python_val, bool):
        return URM_TRUE if python_val else URM_FALSE
    if isinstance(python_val, int):
        return UrmInt(python_val)
    if isinstance(python_val, float):
        return UrmFloat(python_val)
    if isinstance(python_val, str):
        return UrmString(python_val)
    if isinstance(python_val, list):
        return UrmArray([_to_urm_value(v) for v in python_val])
    if isinstance(python_val, dict):
        return UrmDict({_to_hash_key(_to_urm_value(k)): _to_urm_value(v) 
                        for k, v in python_val.items()})
    if isinstance(python_val, tuple):
        return UrmTuple([_to_urm_value(v) for v in python_val])
    if isinstance(python_val, set):
        return UrmSet({_to_hash_key(_to_urm_value(v)) for v in python_val})
    if isinstance(python_val, bytes):
        return UrmBytes(python_val)
    if isinstance(python_val, UrmObject):
        return python_val
    return UrmString(str(python_val))


def _to_python_value(urm_val) -> Any:
    """Convert a UrmObject back to a Python value."""
    if isinstance(urm_val, UrmNone):
        return None
    if isinstance(urm_val, UrmBool):
        return urm_val.value
    if isinstance(urm_val, UrmInt):
        return urm_val.value
    if isinstance(urm_val, UrmFloat):
        return urm_val.value
    if isinstance(urm_val, UrmString):
        return urm_val.value
    if isinstance(urm_val, UrmArray):
        return [_to_python_value(e) for e in urm_val.elements]
    if isinstance(urm_val, UrmDict):
        result = {}
        for k, v in urm_val.pairs.items():
            py_key = _from_hash_key(k)
            if isinstance(py_key, UrmObject):
                py_key = _to_python_value(py_key)
            result[py_key] = _to_python_value(v)
        return result
    if isinstance(urm_val, UrmTuple):
        return tuple(_to_python_value(e) for e in urm_val.elements)
    if isinstance(urm_val, UrmBytes):
        return urm_val.data
    if isinstance(urm_val, UrmError):
        return Exception(urm_val.message)
    return urm_val
