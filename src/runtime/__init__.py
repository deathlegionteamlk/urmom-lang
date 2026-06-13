"""
Urmom Lang Runtime Evaluator
============================
Executes the Urmom Lang AST directly. This is the reference runtime
for the language - a tree-walking evaluator with a custom object model,
environment system, and concurrency primitives.

The evaluator implements Urmom Lang's own semantics:
- Immutable by default (let mut for mutable)
- First-class functions with closures
- Struct/Enum/Trait/Impl type system
- Spawn/Channel/Future concurrency
- Pattern matching, pipe operator, null-safe access
- Comprehensive stdlib modules
"""

from ..ast import *
from ..vm.objects import *
from ..vm.objects import _repr, _eq, _hash, _is_truthy, _to_hash_key, _from_hash_key, _to_urm_value, _to_python_value
from ..vm.opcodes import OpCode
from ..lexer import Lexer
from ..parser import Parser
import threading
import queue
import time
import json
import math
import random
import re
import os
import sys
import hashlib
import base64
import uuid
import datetime
import collections
import itertools


class Environment:
    """Variable scope with parent chain for lexical scoping."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.variables = {}
        self.mutability = {}  # name -> bool (True = mutable)
    
    def define(self, name: str, value, mutable: bool = False):
        self.variables[name] = value
        self.mutability[name] = mutable
    
    def get(self, name: str):
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.get(name)
        raise UrmRuntimeError(f"Undefined variable: {name}")
    
    def set(self, name: str, value):
        if name in self.variables:
            if not self.mutability.get(name, False):
                raise UrmRuntimeError(f"Cannot reassign immutable variable: {name}")
            self.variables[name] = value
            return
        if self.parent:
            self.parent.set(name, value)
            return
        raise UrmRuntimeError(f"Undefined variable: {name}")
    
    def has(self, name: str) -> bool:
        if name in self.variables:
            return True
        if self.parent:
            return self.parent.has(name)
        return False
    
    def child(self) -> 'Environment':
        return Environment(parent=self)


class Evaluator:
    """Urmom Lang AST evaluator - the runtime engine."""
    
    def __init__(self):
        self.global_env = Environment()
        self.module_registry = {}
        self.stdlib = {}
        self._setup_builtins()
        self._setup_stdlib()
        self._output_buffer = []
    
    def _print_output(self, *args, **kwargs):
        """Capture or print output."""
        text = ' '.join(_repr(a) if isinstance(a, UrmObject) else str(a) for a in args)
        if kwargs.get('end', '\n') == '':
            self._output_buffer.append(text)
            print(text, end='')
        else:
            self._output_buffer.append(text)
            print(text)
    
    def _setup_builtins(self):
        """Register all built-in functions."""
        env = self.global_env
        
        # I/O
        env.define("print", UrmBuiltinFn("print", self._builtin_print, -1))
        env.define("println", UrmBuiltinFn("println", self._builtin_println, -1))
        env.define("eprint", UrmBuiltinFn("eprint", self._builtin_eprint, -1))
        env.define("read_line", UrmBuiltinFn("read_line", self._builtin_read_line, 0))
        env.define("read_file", UrmBuiltinFn("read_file", self._builtin_read_file, 1))
        env.define("write_file", UrmBuiltinFn("write_file", self._builtin_write_file, 2))
        env.define("append_file", UrmBuiltinFn("append_file", self._builtin_append_file, 2))
        
        # Type conversion
        env.define("int", UrmBuiltinFn("int", self._builtin_int, 1))
        env.define("float", UrmBuiltinFn("float", self._builtin_float, 1))
        env.define("str", UrmBuiltinFn("str", self._builtin_str, 1))
        env.define("bool", UrmBuiltinFn("bool", self._builtin_bool, 1))
        env.define("bytes", UrmBuiltinFn("bytes", self._builtin_bytes, 1))
        env.define("type_of", UrmBuiltinFn("type_of", self._builtin_type_of, 1))
        env.define("isinstance", UrmBuiltinFn("isinstance", self._builtin_isinstance, 2))
        
        # Collection functions
        env.define("len", UrmBuiltinFn("len", self._builtin_len, 1))
        env.define("range", UrmBuiltinFn("range", self._builtin_range, -1))
        env.define("enumerate", UrmBuiltinFn("enumerate", self._builtin_enumerate, 1))
        env.define("zip", UrmBuiltinFn("zip", self._builtin_zip, -1))
        env.define("map", UrmBuiltinFn("map", self._builtin_map, 2))
        env.define("filter", UrmBuiltinFn("filter", self._builtin_filter, 2))
        env.define("reduce", UrmBuiltinFn("reduce", self._builtin_reduce, 3))
        env.define("sort", UrmBuiltinFn("sort", self._builtin_sort, -1))
        env.define("reverse", UrmBuiltinFn("reverse", self._builtin_reverse, 1))
        env.define("flatten", UrmBuiltinFn("flatten", self._builtin_flatten, -1))
        env.define("unique", UrmBuiltinFn("unique", self._builtin_unique, 1))
        env.define("min", UrmBuiltinFn("min", self._builtin_min, -1))
        env.define("max", UrmBuiltinFn("max", self._builtin_max, -1))
        env.define("sum", UrmBuiltinFn("sum", self._builtin_sum, -1))
        env.define("any", UrmBuiltinFn("any", self._builtin_any, 1))
        env.define("all", UrmBuiltinFn("all", self._builtin_all, 1))
        env.define("contains", UrmBuiltinFn("contains", self._builtin_contains, 2))
        env.define("find", UrmBuiltinFn("find", self._builtin_find, 2))
        env.define("find_index", UrmBuiltinFn("find_index", self._builtin_find_index, 2))
        env.define("chunk", UrmBuiltinFn("chunk", self._builtin_chunk, 2))
        env.define("join", UrmBuiltinFn("join", self._builtin_join, 2))
        env.define("split", UrmBuiltinFn("split", self._builtin_split, -1))
        env.define("trim", UrmBuiltinFn("trim", self._builtin_trim, 1))
        env.define("upper", UrmBuiltinFn("upper", self._builtin_upper, 1))
        env.define("lower", UrmBuiltinFn("lower", self._builtin_lower, 1))
        env.define("replace", UrmBuiltinFn("replace", self._builtin_replace, 3))
        env.define("starts_with", UrmBuiltinFn("starts_with", self._builtin_starts_with, 2))
        env.define("ends_with", UrmBuiltinFn("ends_with", self._builtin_ends_with, 2))
        env.define("char_at", UrmBuiltinFn("char_at", self._builtin_char_at, 2))
        env.define("substring", UrmBuiltinFn("substring", self._builtin_substring, -1))
        env.define("repeat", UrmBuiltinFn("repeat", self._builtin_repeat, 2))
        env.define("reverse_str", UrmBuiltinFn("reverse_str", self._builtin_reverse_str, 1))
        env.define("format", UrmBuiltinFn("format", self._builtin_format, -1))
        
        # Math
        env.define("abs", UrmBuiltinFn("abs", self._builtin_abs, 1))
        env.define("floor", UrmBuiltinFn("floor", self._builtin_floor, 1))
        env.define("ceil", UrmBuiltinFn("ceil", self._builtin_ceil, 1))
        env.define("round", UrmBuiltinFn("round", self._builtin_round, -1))
        env.define("sqrt", UrmBuiltinFn("sqrt", self._builtin_sqrt, 1))
        env.define("pow", UrmBuiltinFn("pow", self._builtin_pow, 2))
        env.define("log", UrmBuiltinFn("log", self._builtin_log, -1))
        env.define("sin", UrmBuiltinFn("sin", self._builtin_sin, 1))
        env.define("cos", UrmBuiltinFn("cos", self._builtin_cos, 1))
        env.define("tan", UrmBuiltinFn("tan", self._builtin_tan, 1))
        env.define("pi", UrmFloat(math.pi))
        env.define("e_num", UrmFloat(math.e))
        env.define("inf", UrmFloat(float('inf')))
        env.define("nan", UrmFloat(float('nan')))
        
        # JSON
        env.define("json_parse", UrmBuiltinFn("json_parse", self._builtin_json_parse, 1))
        env.define("json_stringify", UrmBuiltinFn("json_stringify", self._builtin_json_stringify, -1))
        
        # Time
        env.define("time_now", UrmBuiltinFn("time_now", self._builtin_time_now, 0))
        env.define("time_format", UrmBuiltinFn("time_format", self._builtin_time_format, -1))
        env.define("sleep", UrmBuiltinFn("sleep", self._builtin_sleep, 1))
        
        # Random
        env.define("random", UrmBuiltinFn("random", self._builtin_random, 0))
        env.define("random_int", UrmBuiltinFn("random_int", self._builtin_random_int, 2))
        env.define("random_choice", UrmBuiltinFn("random_choice", self._builtin_random_choice, 1))
        env.define("random_shuffle", UrmBuiltinFn("random_shuffle", self._builtin_random_shuffle, 1))
        
        # Concurrency
        env.define("spawn", UrmBuiltinFn("spawn", self._builtin_spawn, 1))
        env.define("chan", UrmBuiltinFn("chan", self._builtin_chan, -1))
        env.define("select", UrmBuiltinFn("select", self._builtin_select, -1))
        env.define("mutex", UrmBuiltinFn("mutex", self._builtin_mutex, 0))
        
        # Regex
        env.define("regex", UrmBuiltinFn("regex", self._builtin_regex, -1))
        env.define("regex_match", UrmBuiltinFn("regex_match", self._builtin_regex_match, 2))
        env.define("regex_search", UrmBuiltinFn("regex_search", self._builtin_regex_search, 2))
        env.define("regex_replace", UrmBuiltinFn("regex_replace", self._builtin_regex_replace, 3))
        env.define("regex_split", UrmBuiltinFn("regex_split", self._builtin_regex_split, 2))
        env.define("regex_find_all", UrmBuiltinFn("regex_find_all", self._builtin_regex_find_all, 2))
        
        # Hashing / Encoding
        env.define("md5", UrmBuiltinFn("md5", self._builtin_md5, 1))
        env.define("sha256", UrmBuiltinFn("sha256", self._builtin_sha256, 1))
        env.define("sha512", UrmBuiltinFn("sha512", self._builtin_sha512, 1))
        env.define("base64_encode", UrmBuiltinFn("base64_encode", self._builtin_base64_encode, 1))
        env.define("base64_decode", UrmBuiltinFn("base64_decode", self._builtin_base64_decode, 1))
        env.define("hex_encode", UrmBuiltinFn("hex_encode", self._builtin_hex_encode, 1))
        env.define("hex_decode", UrmBuiltinFn("hex_decode", self._builtin_hex_decode, 1))
        env.define("url_encode", UrmBuiltinFn("url_encode", self._builtin_url_encode, 1))
        env.define("url_decode", UrmBuiltinFn("url_decode", self._builtin_url_decode, 1))
        
        # UUID
        env.define("uuid", UrmBuiltinFn("uuid", self._builtin_uuid, 0))
        env.define("uuid_v4", UrmBuiltinFn("uuid_v4", self._builtin_uuid_v4, 0))
        
        # OS / Process
        env.define("env_get", UrmBuiltinFn("env_get", self._builtin_env_get, 1))
        env.define("env_set", UrmBuiltinFn("env_set", self._builtin_env_set, 2))
        env.define("cwd", UrmBuiltinFn("cwd", self._builtin_cwd, 0))
        env.define("args", UrmBuiltinFn("args", self._builtin_args, 0))
        env.define("exec", UrmBuiltinFn("exec", self._builtin_exec, 1))
        env.define("exit", UrmBuiltinFn("exit", self._builtin_exit, -1))
        
        # File system
        env.define("file_exists", UrmBuiltinFn("file_exists", self._builtin_file_exists, 1))
        env.define("file_size", UrmBuiltinFn("file_size", self._builtin_file_size, 1))
        env.define("is_dir", UrmBuiltinFn("is_dir", self._builtin_is_dir, 1))
        env.define("is_file", UrmBuiltinFn("is_file", self._builtin_is_file, 1))
        env.define("list_dir", UrmBuiltinFn("list_dir", self._builtin_list_dir, -1))
        env.define("make_dir", UrmBuiltinFn("make_dir", self._builtin_make_dir, 1))
        env.define("remove", UrmBuiltinFn("remove", self._builtin_remove, 1))
        env.define("rename", UrmBuiltinFn("rename", self._builtin_rename, 2))
        env.define("copy", UrmBuiltinFn("copy", self._builtin_copy, 2))
        env.define("path_join", UrmBuiltinFn("path_join", self._builtin_path_join, -1))
        env.define("path_split", UrmBuiltinFn("path_split", self._builtin_path_split, 1))
        env.define("path_ext", UrmBuiltinFn("path_ext", self._builtin_path_ext, 1))
        env.define("path_base", UrmBuiltinFn("path_base", self._builtin_path_base, 1))
        env.define("path_dir", UrmBuiltinFn("path_dir", self._builtin_path_dir, 1))
        
        # Error handling
        env.define("panic", UrmBuiltinFn("panic", self._builtin_panic, -1))
        env.define("error", UrmBuiltinFn("error", self._builtin_error, -1))
        
        # Itertools
        env.define("iterate", UrmBuiltinFn("iterate", self._builtin_iterate, 1))
        env.define("take", UrmBuiltinFn("take", self._builtin_take, 2))
        env.define("drop", UrmBuiltinFn("drop", self._builtin_drop, 2))
        env.define("cycle", UrmBuiltinFn("cycle", self._builtin_cycle, 1))
        env.define("count", UrmBuiltinFn("count", self._builtin_count, -1))
        env.define("chain", UrmBuiltinFn("chain", self._builtin_chain, -1))
        env.define("product", UrmBuiltinFn("product", self._builtin_product, -1))
        env.define("permutations", UrmBuiltinFn("permutations", self._builtin_permutations, -1))
        env.define("combinations", UrmBuiltinFn("combinations", self._builtin_combinations, 2))
        env.define("group_by", UrmBuiltinFn("group_by", self._builtin_group_by, 2))
        env.define("partition", UrmBuiltinFn("partition", self._builtin_partition, 2))
        
        # Memoization
        env.define("memoize", UrmBuiltinFn("memoize", self._builtin_memoize, 1))
        
        # Deep operations
        env.define("deep_copy", UrmBuiltinFn("deep_copy", self._builtin_deep_copy, 1))
        env.define("deep_eq", UrmBuiltinFn("deep_eq", self._builtin_deep_eq, 2))
        
        # String padding
        env.define("pad_left", UrmBuiltinFn("pad_left", self._builtin_pad_left, 3))
        env.define("pad_right", UrmBuiltinFn("pad_right", self._builtin_pad_right, 3))
        
        # Array specific
        env.define("push", UrmBuiltinFn("push", self._builtin_push, 2))
        env.define("pop", UrmBuiltinFn("pop", self._builtin_pop, 1))
        env.define("insert", UrmBuiltinFn("insert", self._builtin_insert, 3))
        env.define("remove_at", UrmBuiltinFn("remove_at", self._builtin_remove_at, 2))
    
    def _setup_stdlib(self):
        """Set up standard library modules."""
        self.stdlib = {
            "std.io": self._make_io_module(),
            "std.fs": self._make_fs_module(),
            "std.net": self._make_net_module(),
            "std.math": self._make_math_module(),
            "std.time": self._make_time_module(),
            "std.data": self._make_data_module(),
            "std.rand": self._make_rand_module(),
            "std.regex": self._make_regex_module(),
            "std.concurrency": self._make_concurrency_module(),
            "std.crypto": self._make_crypto_module(),
            "std.encoding": self._make_encoding_module(),
            "std.os": self._make_os_module(),
            "std.process": self._make_process_module(),
            "std.path": self._make_path_module(),
            "std.uuid": self._make_uuid_module(),
            "std.collections": self._make_collections_module(),
        }
    
    def _make_module(self, name, entries):
        """Helper to create a module from a dict of name -> UrmObject."""
        mod = UrmModule(name=name)
        for k, v in entries.items():
            if isinstance(v, UrmObject):
                mod.exports[k] = v
            else:
                mod.exports[k] = _to_urm_value(v)
        return mod
    
    def _make_io_module(self):
        return self._make_module("std.io", {
            "print": UrmBuiltinFn("print", self._builtin_print, -1),
            "println": UrmBuiltinFn("println", self._builtin_println, -1),
            "eprint": UrmBuiltinFn("eprint", self._builtin_eprint, -1),
            "read_line": UrmBuiltinFn("read_line", self._builtin_read_line, 0),
            "read_file": UrmBuiltinFn("read_file", self._builtin_read_file, 1),
            "write_file": UrmBuiltinFn("write_file", self._builtin_write_file, 2),
        })
    
    def _make_fs_module(self):
        return self._make_module("std.fs", {
            "exists": UrmBuiltinFn("exists", self._builtin_file_exists, 1),
            "size": UrmBuiltinFn("size", self._builtin_file_size, 1),
            "is_dir": UrmBuiltinFn("is_dir", self._builtin_is_dir, 1),
            "is_file": UrmBuiltinFn("is_file", self._builtin_is_file, 1),
            "list_dir": UrmBuiltinFn("list_dir", self._builtin_list_dir, -1),
            "make_dir": UrmBuiltinFn("make_dir", self._builtin_make_dir, 1),
            "remove": UrmBuiltinFn("remove", self._builtin_remove, 1),
            "rename": UrmBuiltinFn("rename", self._builtin_rename, 2),
            "copy": UrmBuiltinFn("copy", self._builtin_copy, 2),
            "read": UrmBuiltinFn("read", self._builtin_read_file, 1),
            "write": UrmBuiltinFn("write", self._builtin_write_file, 2),
            "append": UrmBuiltinFn("append", self._builtin_append_file, 2),
        })
    
    def _make_net_module(self):
        def _http_get(args):
            try:
                import urllib.request
                url = _to_python_value(args[0]) if args else ""
                with urllib.request.urlopen(url, timeout=10) as resp:
                    return UrmString(resp.read().decode('utf-8'))
            except Exception as e:
                return UrmError("NetworkError", str(e))
        
        def _http_post(args):
            try:
                import urllib.request
                url = _to_python_value(args[0])
                data = _to_python_value(args[1]) if len(args) > 1 else b""
                if isinstance(data, str):
                    data = data.encode()
                req = urllib.request.Request(url, data=data, method='POST')
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return UrmString(resp.read().decode('utf-8'))
            except Exception as e:
                return UrmError("NetworkError", str(e))
        
        def _dns_resolve(args):
            import socket
            try:
                host = _to_python_value(args[0])
                addrs = socket.getaddrinfo(host, None)
                return UrmArray([UrmString(a[4][0]) for a in addrs[:10]])
            except Exception as e:
                return UrmError("DNSError", str(e))
        
        def _url_parse(args):
            from urllib.parse import urlparse, parse_qs
            url = _to_python_value(args[0])
            p = urlparse(url)
            return UrmDict({
                "scheme": UrmString(p.scheme),
                "host": UrmString(p.hostname or ""),
                "port": UrmInt(p.port or 0),
                "path": UrmString(p.path),
                "query": UrmString(p.query),
                "fragment": UrmString(p.fragment),
            })
        
        return self._make_module("std.net", {
            "http_get": UrmBuiltinFn("http_get", _http_get, 1),
            "http_post": UrmBuiltinFn("http_post", _http_post, 2),
            "dns_resolve": UrmBuiltinFn("dns_resolve", _dns_resolve, 1),
            "url_parse": UrmBuiltinFn("url_parse", _url_parse, 1),
        })
    
    def _make_math_module(self):
        return self._make_module("std.math", {
            "abs": UrmBuiltinFn("abs", self._builtin_abs, 1),
            "floor": UrmBuiltinFn("floor", self._builtin_floor, 1),
            "ceil": UrmBuiltinFn("ceil", self._builtin_ceil, 1),
            "round": UrmBuiltinFn("round", self._builtin_round, -1),
            "sqrt": UrmBuiltinFn("sqrt", self._builtin_sqrt, 1),
            "pow": UrmBuiltinFn("pow", self._builtin_pow, 2),
            "log": UrmBuiltinFn("log", self._builtin_log, -1),
            "sin": UrmBuiltinFn("sin", self._builtin_sin, 1),
            "cos": UrmBuiltinFn("cos", self._builtin_cos, 1),
            "tan": UrmBuiltinFn("tan", self._builtin_tan, 1),
            "asin": UrmBuiltinFn("asin", lambda a: UrmFloat(math.asin(_to_python_value(a[0]))), 1),
            "acos": UrmBuiltinFn("acos", lambda a: UrmFloat(math.acos(_to_python_value(a[0]))), 1),
            "atan": UrmBuiltinFn("atan", lambda a: UrmFloat(math.atan(_to_python_value(a[0]))), 1),
            "atan2": UrmBuiltinFn("atan2", lambda a: UrmFloat(math.atan2(_to_python_value(a[0]), _to_python_value(a[1]))), 2),
            "pi": UrmFloat(math.pi),
            "e": UrmFloat(math.e),
            "inf": UrmFloat(float('inf')),
            "gcd": UrmBuiltinFn("gcd", lambda a: UrmInt(math.gcd(int(_to_python_value(a[0])), int(_to_python_value(a[1])))), 2),
            "lcm": UrmBuiltinFn("lcm", lambda a: UrmInt(abs(int(_to_python_value(a[0])) * int(_to_python_value(a[1]))) // math.gcd(int(_to_python_value(a[0])), int(_to_python_value(a[1])))), 2),
            "clamp": UrmBuiltinFn("clamp", lambda a: _to_urm_value(max(_to_python_value(a[1]), min(_to_python_value(a[2]), _to_python_value(a[0])))), 3),
            "sign": UrmBuiltinFn("sign", lambda a: UrmInt((1 if _to_python_value(a[0]) > 0 else (-1 if _to_python_value(a[0]) < 0 else 0))), 1),
            "is_nan": UrmBuiltinFn("is_nan", lambda a: UrmBool(math.isnan(_to_python_value(a[0])) if isinstance(_to_python_value(a[0]), float) else False), 1),
            "is_inf": UrmBuiltinFn("is_inf", lambda a: UrmBool(math.isinf(_to_python_value(a[0])) if isinstance(_to_python_value(a[0]), float) else False), 1),
        })
    
    def _make_time_module(self):
        return self._make_module("std.time", {
            "now": UrmBuiltinFn("now", self._builtin_time_now, 0),
            "format": UrmBuiltinFn("format", self._builtin_time_format, -1),
            "sleep": UrmBuiltinFn("sleep", self._builtin_sleep, 1),
            "unix": UrmBuiltinFn("unix", lambda a: UrmFloat(time.time()), 0),
            "date": UrmBuiltinFn("date", lambda a: UrmString(datetime.datetime.now().strftime("%Y-%m-%d")), 0),
            "time": UrmBuiltinFn("time", lambda a: UrmString(datetime.datetime.now().strftime("%H:%M:%S")), 0),
            "datetime": UrmBuiltinFn("datetime", lambda a: UrmString(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 0),
        })
    
    def _make_data_module(self):
        return self._make_module("std.data", {
            "json_parse": UrmBuiltinFn("json_parse", self._builtin_json_parse, 1),
            "json_stringify": UrmBuiltinFn("json_stringify", self._builtin_json_stringify, -1),
            "csv_parse": UrmBuiltinFn("csv_parse", lambda a: self._csv_parse(a), 1),
            "sort": UrmBuiltinFn("sort", self._builtin_sort, -1),
            "group_by": UrmBuiltinFn("group_by", self._builtin_group_by, 2),
            "partition": UrmBuiltinFn("partition", self._builtin_partition, 2),
            "chunk": UrmBuiltinFn("chunk", self._builtin_chunk, 2),
            "flatten": UrmBuiltinFn("flatten", self._builtin_flatten, -1),
            "unique": UrmBuiltinFn("unique", self._builtin_unique, 1),
        })
    
    def _make_rand_module(self):
        return self._make_module("std.rand", {
            "random": UrmBuiltinFn("random", self._builtin_random, 0),
            "int": UrmBuiltinFn("int", self._builtin_random_int, 2),
            "choice": UrmBuiltinFn("choice", self._builtin_random_choice, 1),
            "shuffle": UrmBuiltinFn("shuffle", self._builtin_random_shuffle, 1),
            "seed": UrmBuiltinFn("seed", lambda a: (random.seed(int(_to_python_value(a[0]))), URM_NONE)[1], 1),
        })
    
    def _make_regex_module(self):
        return self._make_module("std.regex", {
            "compile": UrmBuiltinFn("compile", self._builtin_regex, -1),
            "match": UrmBuiltinFn("match", self._builtin_regex_match, 2),
            "search": UrmBuiltinFn("search", self._builtin_regex_search, 2),
            "replace": UrmBuiltinFn("replace", self._builtin_regex_replace, 3),
            "split": UrmBuiltinFn("split", self._builtin_regex_split, 2),
            "find_all": UrmBuiltinFn("find_all", self._builtin_regex_find_all, 2),
        })
    
    def _make_concurrency_module(self):
        return self._make_module("std.concurrency", {
            "spawn": UrmBuiltinFn("spawn", self._builtin_spawn, 1),
            "chan": UrmBuiltinFn("chan", self._builtin_chan, -1),
            "select": UrmBuiltinFn("select", self._builtin_select, -1),
            "mutex": UrmBuiltinFn("mutex", self._builtin_mutex, 0),
            "sleep": UrmBuiltinFn("sleep", self._builtin_sleep, 1),
        })
    
    def _make_crypto_module(self):
        return self._make_module("std.crypto", {
            "md5": UrmBuiltinFn("md5", self._builtin_md5, 1),
            "sha256": UrmBuiltinFn("sha256", self._builtin_sha256, 1),
            "sha512": UrmBuiltinFn("sha512", self._builtin_sha512, 1),
            "hmac_sha256": UrmBuiltinFn("hmac_sha256", lambda a: UrmString(hashlib.new('sha256', _to_python_value(a[1]).encode()).hexdigest()), 2),
        })
    
    def _make_encoding_module(self):
        return self._make_module("std.encoding", {
            "base64_encode": UrmBuiltinFn("base64_encode", self._builtin_base64_encode, 1),
            "base64_decode": UrmBuiltinFn("base64_decode", self._builtin_base64_decode, 1),
            "hex_encode": UrmBuiltinFn("hex_encode", self._builtin_hex_encode, 1),
            "hex_decode": UrmBuiltinFn("hex_decode", self._builtin_hex_decode, 1),
            "url_encode": UrmBuiltinFn("url_encode", self._builtin_url_encode, 1),
            "url_decode": UrmBuiltinFn("url_decode", self._builtin_url_decode, 1),
        })
    
    def _make_os_module(self):
        return self._make_module("std.os", {
            "env_get": UrmBuiltinFn("env_get", self._builtin_env_get, 1),
            "env_set": UrmBuiltinFn("env_set", self._builtin_env_set, 2),
            "cwd": UrmBuiltinFn("cwd", self._builtin_cwd, 0),
            "args": UrmBuiltinFn("args", self._builtin_args, 0),
            "exit": UrmBuiltinFn("exit", self._builtin_exit, -1),
            "hostname": UrmBuiltinFn("hostname", lambda a: UrmString(os.uname().nodename if hasattr(os, 'uname') else os.environ.get('COMPUTERNAME', 'localhost')), 0),
            "platform": UrmBuiltinFn("platform", lambda a: UrmString(sys.platform), 0),
            "pid": UrmBuiltinFn("pid", lambda a: UrmInt(os.getpid()), 0),
            "arch": UrmBuiltinFn("arch", lambda a: UrmString(os.environ.get('PROCESSOR_ARCHITECTURE', sys.maxsize > 2**32 and 'x64' or 'x86')), 0),
        })
    
    def _make_process_module(self):
        return self._make_module("std.process", {
            "exec": UrmBuiltinFn("exec", self._builtin_exec, 1),
            "spawn": UrmBuiltinFn("spawn", self._builtin_exec, 1),
        })
    
    def _make_path_module(self):
        return self._make_module("std.path", {
            "join": UrmBuiltinFn("join", self._builtin_path_join, -1),
            "split": UrmBuiltinFn("split", self._builtin_path_split, 1),
            "ext": UrmBuiltinFn("ext", self._builtin_path_ext, 1),
            "base": UrmBuiltinFn("base", self._builtin_path_base, 1),
            "dir": UrmBuiltinFn("dir", self._builtin_path_dir, 1),
            "exists": UrmBuiltinFn("exists", self._builtin_file_exists, 1),
        })
    
    def _make_uuid_module(self):
        return self._make_module("std.uuid", {
            "v4": UrmBuiltinFn("v4", self._builtin_uuid_v4, 0),
            "v1": UrmBuiltinFn("v1", lambda a: UrmString(str(uuid.uuid1())), 0),
            "nil": UrmBuiltinFn("nil", lambda a: UrmString("00000000-0000-0000-0000-000000000000"), 0),
            "is_valid": UrmBuiltinFn("is_valid", lambda a: UrmBool(bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', _to_python_value(a[0]), re.I))), 1),
        })
    
    def _make_collections_module(self):
        return self._make_module("std.collections", {
            "counter": UrmBuiltinFn("counter", lambda a: self._builtin_counter(a), 1),
            "deque": UrmBuiltinFn("deque", lambda a: UrmArray(), -1),
            "chain": UrmBuiltinFn("chain", self._builtin_chain, -1),
            "group_by": UrmBuiltinFn("group_by", self._builtin_group_by, 2),
            "permutations": UrmBuiltinFn("permutations", self._builtin_permutations, -1),
            "combinations": UrmBuiltinFn("combinations", self._builtin_combinations, 2),
        })
    
    # ═══════════════════════════════════════════════════════════
    # Built-in Function Implementations
    # ═══════════════════════════════════════════════════════════
    
    def _builtin_print(self, *args):
        self._print_output(*args, end='')
        return URM_NONE
    
    def _builtin_println(self, *args):
        self._print_output(*args)
        return URM_NONE
    
    def _builtin_eprint(self, *args):
        text = ' '.join(_repr(a) if isinstance(a, UrmObject) else str(a) for a in args)
        print(text, file=sys.stderr)
        return URM_NONE
    
    def _builtin_read_line(self, *args):
        try:
            line = input()
            return UrmString(line)
        except EOFError:
            return URM_NONE
    
    def _builtin_read_file(self, *args):
        path = _to_python_value(args[0])
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return UrmString(f.read())
        except Exception as e:
            return UrmError("FileError", str(e))
    
    def _builtin_write_file(self, *args):
        path = _to_python_value(args[0])
        content = _to_python_value(args[1])
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(str(content))
            return URM_NONE
        except Exception as e:
            return UrmError("FileError", str(e))
    
    def _builtin_append_file(self, *args):
        path = _to_python_value(args[0])
        content = _to_python_value(args[1])
        try:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(str(content))
            return URM_NONE
        except Exception as e:
            return UrmError("FileError", str(e))
    
    def _builtin_int(self, *args):
        v = _to_python_value(args[0])
        try:
            return UrmInt(int(v))
        except (ValueError, TypeError):
            return UrmInt(0)
    
    def _builtin_float(self, *args):
        v = _to_python_value(args[0])
        try:
            return UrmFloat(float(v))
        except (ValueError, TypeError):
            return UrmFloat(0.0)
    
    def _builtin_str(self, *args):
        v = args[0]
        if isinstance(v, UrmObject):
            return UrmString(v.urm_repr())
        return UrmString(str(v))
    
    def _builtin_bool(self, *args):
        return URM_TRUE if _is_truthy(args[0]) else URM_FALSE
    
    def _builtin_bytes(self, *args):
        v = _to_python_value(args[0])
        if isinstance(v, str):
            return UrmBytes(v.encode('utf-8'))
        if isinstance(v, int):
            return UrmBytes(bytes([v]))
        return UrmBytes(b"")
    
    def _builtin_type_of(self, *args):
        v = args[0]
        if isinstance(v, UrmObject):
            return UrmString(v.urm_type_name())
        return UrmString(type(v).__name__)
    
    def _builtin_isinstance(self, *args):
        obj = args[0]
        type_name = _to_python_value(args[1])
        if isinstance(obj, UrmObject):
            return UrmBool(obj.urm_type_name() == type_name)
        return URM_FALSE
    
    def _builtin_len(self, *args):
        v = args[0]
        if isinstance(v, UrmArray): return UrmInt(v.length())
        if isinstance(v, UrmString): return UrmInt(len(v.value))
        if isinstance(v, UrmDict): return UrmInt(v.length())
        if isinstance(v, UrmTuple): return UrmInt(len(v.elements))
        if isinstance(v, UrmSet): return UrmInt(len(v.elements))
        if isinstance(v, UrmBytes): return UrmInt(v.length())
        if isinstance(v, UrmRange): return UrmInt(v.length())
        return UrmInt(0)
    
    def _builtin_range(self, *args):
        if len(args) == 1:
            end = _to_python_value(args[0])
            return UrmRange(0, end, 1, False)
        elif len(args) == 2:
            start = _to_python_value(args[0])
            end = _to_python_value(args[1])
            return UrmRange(start, end, 1, False)
        elif len(args) >= 3:
            start = _to_python_value(args[0])
            end = _to_python_value(args[1])
            step = _to_python_value(args[2])
            inclusive = _to_python_value(args[3]) if len(args) > 3 else False
            return UrmRange(start, end, step, inclusive)
        return UrmRange(0, 0, 1, False)
    
    def _builtin_enumerate(self, *args):
        arr = args[0]
        if isinstance(arr, UrmArray):
            result = UrmArray([UrmArray([UrmInt(i), e]) for i, e in enumerate(arr.elements)])
            return result
        return UrmArray()
    
    def _builtin_zip(self, *args):
        arrays = [a for a in args if isinstance(a, UrmArray)]
        if not arrays:
            return UrmArray()
        min_len = min(len(a.elements) for a in arrays)
        result = []
        for i in range(min_len):
            result.append(UrmArray([a.elements[i] for a in arrays]))
        return UrmArray(result)
    
    def _builtin_map(self, *args):
        fn, arr = args[0], args[1]
        if isinstance(arr, UrmArray):
            result = []
            for e in arr.elements:
                result.append(self._call_function(fn, [e]))
            return UrmArray(result)
        return UrmArray()
    
    def _builtin_filter(self, *args):
        fn, arr = args[0], args[1]
        if isinstance(arr, UrmArray):
            result = []
            for e in arr.elements:
                if _is_truthy(self._call_function(fn, [e])):
                    result.append(e)
            return UrmArray(result)
        return UrmArray()
    
    def _builtin_reduce(self, *args):
        fn = args[0]
        arr = args[1]
        init = args[2] if len(args) > 2 else None
        if isinstance(arr, UrmArray):
            acc = init if init is not None else arr.elements[0]
            start = 0 if init is not None else 1
            for e in arr.elements[start:]:
                acc = self._call_function(fn, [acc, e])
            return acc
        return URM_NONE
    
    def _builtin_sort(self, *args):
        arr = args[0]
        fn = args[1] if len(args) > 1 else None
        if isinstance(arr, UrmArray):
            result = UrmArray(list(arr.elements))
            if fn:
                result.elements.sort(key=lambda x: _to_python_value(self._call_function(fn, [x])))
            else:
                result.elements.sort(key=lambda x: x.value if hasattr(x, 'value') else str(x))
            return result
        return arr
    
    def _builtin_reverse(self, *args):
        arr = args[0]
        if isinstance(arr, UrmArray):
            result = UrmArray(list(arr.elements))
            result.reverse()
            return result
        if isinstance(arr, UrmString):
            return UrmString(arr.value[::-1])
        return arr
    
    def _builtin_flatten(self, *args):
        arr = args[0]
        depth = _to_python_value(args[1]) if len(args) > 1 else 1
        if isinstance(arr, UrmArray):
            return arr.flat(depth)
        return arr
    
    def _builtin_unique(self, *args):
        arr = args[0]
        if isinstance(arr, UrmArray):
            return arr.unique()
        return arr
    
    def _builtin_min(self, *args):
        if len(args) == 1 and isinstance(args[0], UrmArray):
            vals = args[0].elements
        else:
            vals = list(args)
        if not vals:
            return URM_NONE
        return min(vals, key=lambda x: x.value if hasattr(x, 'value') else 0)
    
    def _builtin_max(self, *args):
        if len(args) == 1 and isinstance(args[0], UrmArray):
            vals = args[0].elements
        else:
            vals = list(args)
        if not vals:
            return URM_NONE
        return max(vals, key=lambda x: x.value if hasattr(x, 'value') else 0)
    
    def _builtin_sum(self, *args):
        if len(args) == 1 and isinstance(args[0], UrmArray):
            vals = args[0].elements
        else:
            vals = list(args)
        total = 0
        for v in vals:
            if isinstance(v, (UrmInt, UrmFloat)):
                total += v.value
        if isinstance(total, float):
            return UrmFloat(total)
        return UrmInt(total)
    
    def _builtin_any(self, *args):
        arr = args[0]
        if isinstance(arr, UrmArray):
            return UrmBool(any(_is_truthy(e) for e in arr.elements))
        return URM_FALSE
    
    def _builtin_all(self, *args):
        arr = args[0]
        if isinstance(arr, UrmArray):
            return UrmBool(all(_is_truthy(e) for e in arr.elements))
        return URM_TRUE
    
    def _builtin_contains(self, *args):
        collection, val = args[0], args[1]
        if isinstance(collection, UrmArray):
            return collection.contains(val)
        if isinstance(collection, UrmString):
            return UrmBool(_to_python_value(val) in collection.value)
        if isinstance(collection, UrmDict):
            return UrmBool(collection.has(val))
        if isinstance(collection, UrmSet):
            return UrmBool(collection.has(val))
        return URM_FALSE
    
    def _builtin_find(self, *args):
        fn, arr = args[0], args[1]
        if isinstance(arr, UrmArray):
            for e in arr.elements:
                if _is_truthy(self._call_function(fn, [e])):
                    return e
        return URM_NONE
    
    def _builtin_find_index(self, *args):
        fn, arr = args[0], args[1]
        if isinstance(arr, UrmArray):
            for i, e in enumerate(arr.elements):
                if _is_truthy(self._call_function(fn, [e])):
                    return UrmInt(i)
        return URM_NONE
    
    def _builtin_chunk(self, *args):
        arr, size = args[0], args[1]
        if isinstance(arr, UrmArray):
            return arr.chunk(size)
        return UrmArray()
    
    def _builtin_join(self, *args):
        sep, arr = args[0], args[1]
        sep_str = _to_python_value(sep)
        if isinstance(arr, UrmArray):
            items = [_repr(e) for e in arr.elements]
            return UrmString(sep_str.join(items))
        return UrmString("")
    
    def _builtin_split(self, *args):
        s = _to_python_value(args[0])
        sep = _to_python_value(args[1]) if len(args) > 1 else None
        if sep:
            parts = s.split(sep)
        else:
            parts = s.split()
        return UrmArray([UrmString(p) for p in parts])
    
    def _builtin_trim(self, *args):
        return UrmString(_to_python_value(args[0]).strip())
    
    def _builtin_upper(self, *args):
        return UrmString(_to_python_value(args[0]).upper())
    
    def _builtin_lower(self, *args):
        return UrmString(_to_python_value(args[0]).lower())
    
    def _builtin_replace(self, *args):
        s = _to_python_value(args[0])
        old = _to_python_value(args[1])
        new = _to_python_value(args[2])
        return UrmString(s.replace(old, new))
    
    def _builtin_starts_with(self, *args):
        s = _to_python_value(args[0])
        prefix = _to_python_value(args[1])
        return UrmBool(s.startswith(prefix))
    
    def _builtin_ends_with(self, *args):
        s = _to_python_value(args[0])
        suffix = _to_python_value(args[1])
        return UrmBool(s.endswith(suffix))
    
    def _builtin_char_at(self, *args):
        s = _to_python_value(args[0])
        idx = _to_python_value(args[1])
        if 0 <= idx < len(s):
            return UrmString(s[idx])
        return URM_NONE
    
    def _builtin_substring(self, *args):
        s = _to_python_value(args[0])
        start = _to_python_value(args[1])
        end = _to_python_value(args[2]) if len(args) > 2 else len(s)
        return UrmString(s[start:end])
    
    def _builtin_repeat(self, *args):
        s = _to_python_value(args[0])
        n = _to_python_value(args[1])
        return UrmString(s * n)
    
    def _builtin_reverse_str(self, *args):
        return UrmString(_to_python_value(args[0])[::-1])
    
    def _builtin_format(self, *args):
        template = _to_python_value(args[0])
        vals = [_to_python_value(a) for a in args[1:]]
        try:
            return UrmString(template.format(*vals))
        except:
            return UrmString(template)
    
    def _builtin_abs(self, *args):
        v = _to_python_value(args[0])
        if isinstance(v, int): return UrmInt(abs(v))
        return UrmFloat(abs(v))
    
    def _builtin_floor(self, *args):
        return UrmInt(math.floor(_to_python_value(args[0])))
    
    def _builtin_ceil(self, *args):
        return UrmInt(math.ceil(_to_python_value(args[0])))
    
    def _builtin_round(self, *args):
        v = _to_python_value(args[0])
        ndigits = _to_python_value(args[1]) if len(args) > 1 else 0
        return UrmFloat(round(v, ndigits)) if ndigits else UrmInt(round(v))
    
    def _builtin_sqrt(self, *args):
        return UrmFloat(math.sqrt(_to_python_value(args[0])))
    
    def _builtin_pow(self, *args):
        base = _to_python_value(args[0])
        exp = _to_python_value(args[1])
        result = base ** exp
        if isinstance(result, float) and result == int(result):
            return UrmInt(int(result))
        return _to_urm_value(result)
    
    def _builtin_log(self, *args):
        v = _to_python_value(args[0])
        base = _to_python_value(args[1]) if len(args) > 1 else math.e
        return UrmFloat(math.log(v, base))
    
    def _builtin_sin(self, *args):
        return UrmFloat(math.sin(_to_python_value(args[0])))
    
    def _builtin_cos(self, *args):
        return UrmFloat(math.cos(_to_python_value(args[0])))
    
    def _builtin_tan(self, *args):
        return UrmFloat(math.tan(_to_python_value(args[0])))
    
    def _builtin_json_parse(self, *args):
        try:
            data = json.loads(_to_python_value(args[0]))
            return _to_urm_value(data)
        except Exception as e:
            return UrmError("JSONError", str(e))
    
    def _builtin_json_stringify(self, *args):
        try:
            val = _to_python_value(args[0])
            indent = _to_python_value(args[1]) if len(args) > 1 else 2
            return UrmString(json.dumps(val, indent=indent, ensure_ascii=False))
        except Exception as e:
            return UrmError("JSONError", str(e))
    
    def _builtin_time_now(self, *args):
        return UrmFloat(time.time())
    
    def _builtin_time_format(self, *args):
        fmt = _to_python_value(args[0]) if args else "%Y-%m-%d %H:%M:%S"
        ts = _to_python_value(args[1]) if len(args) > 1 else time.time()
        return UrmString(datetime.datetime.fromtimestamp(ts).strftime(fmt))
    
    def _builtin_sleep(self, *args):
        seconds = _to_python_value(args[0])
        time.sleep(seconds)
        return URM_NONE
    
    def _builtin_random(self, *args):
        return UrmFloat(random.random())
    
    def _builtin_random_int(self, *args):
        lo = _to_python_value(args[0])
        hi = _to_python_value(args[1])
        return UrmInt(random.randint(lo, hi))
    
    def _builtin_random_choice(self, *args):
        arr = args[0]
        if isinstance(arr, UrmArray) and arr.elements:
            return random.choice(arr.elements)
        return URM_NONE
    
    def _builtin_random_shuffle(self, *args):
        arr = args[0]
        if isinstance(arr, UrmArray):
            result = UrmArray(list(arr.elements))
            random.shuffle(result.elements)
            return result
        return arr
    
    def _builtin_spawn(self, *args):
        fn = args[0]
        future = UrmFuture()
        
        def run():
            try:
                result = self._call_function(fn, [])
                future.set_result(result)
            except Exception as e:
                future.set_error(UrmRuntimeError(str(e)))
        
        t = threading.Thread(target=run, daemon=True)
        future._thread = t
        t.start()
        return future
    
    def _builtin_chan(self, *args):
        cap = _to_python_value(args[0]) if args else 0
        return UrmChannel(capacity=cap)
    
    def _builtin_select(self, *args):
        channels = [a for a in args if isinstance(a, UrmChannel)]
        for ch in channels:
            val = ch.try_receive()
            if val is not URM_NONE and not isinstance(val, UrmNone):
                return UrmArray([ch, val])
        # Block briefly
        for ch in channels:
            val = ch.receive(timeout=0.1)
            if not isinstance(val, UrmNone):
                return UrmArray([ch, val])
        return URM_NONE
    
    def _builtin_mutex(self, *args):
        return UrmMutex()
    
    def _builtin_regex(self, *args):
        pattern = _to_python_value(args[0])
        flags = 0
        if len(args) > 1:
            flag_str = _to_python_value(args[1])
            if 'i' in flag_str: flags |= re.IGNORECASE
            if 'm' in flag_str: flags |= re.MULTILINE
            if 's' in flag_str: flags |= re.DOTALL
        return UrmRegex(pattern, flags=flags)
    
    def _builtin_regex_match(self, *args):
        pattern, text = _to_python_value(args[0]), _to_python_value(args[1])
        m = re.match(pattern, text)
        if m:
            return UrmArray([UrmString(m.group(0))] + [UrmString(g) for g in m.groups()])
        return URM_NONE
    
    def _builtin_regex_search(self, *args):
        pattern, text = _to_python_value(args[0]), _to_python_value(args[1])
        m = re.search(pattern, text)
        if m:
            return UrmArray([UrmString(m.group(0))] + [UrmString(g) for g in m.groups()])
        return URM_NONE
    
    def _builtin_regex_replace(self, *args):
        pattern, text, replacement = _to_python_value(args[0]), _to_python_value(args[1]), _to_python_value(args[2])
        return UrmString(re.sub(pattern, replacement, text))
    
    def _builtin_regex_split(self, *args):
        pattern, text = _to_python_value(args[0]), _to_python_value(args[1])
        return UrmArray([UrmString(p) for p in re.split(pattern, text)])
    
    def _builtin_regex_find_all(self, *args):
        pattern, text = _to_python_value(args[0]), _to_python_value(args[1])
        return UrmArray([UrmString(m) for m in re.findall(pattern, text)])
    
    def _builtin_md5(self, *args):
        data = _to_python_value(args[0])
        if isinstance(data, str): data = data.encode()
        return UrmString(hashlib.md5(data).hexdigest())
    
    def _builtin_sha256(self, *args):
        data = _to_python_value(args[0])
        if isinstance(data, str): data = data.encode()
        return UrmString(hashlib.sha256(data).hexdigest())
    
    def _builtin_sha512(self, *args):
        data = _to_python_value(args[0])
        if isinstance(data, str): data = data.encode()
        return UrmString(hashlib.sha512(data).hexdigest())
    
    def _builtin_base64_encode(self, *args):
        data = _to_python_value(args[0])
        if isinstance(data, str): data = data.encode()
        return UrmString(base64.b64encode(data).decode())
    
    def _builtin_base64_decode(self, *args):
        data = _to_python_value(args[0])
        return UrmString(base64.b64decode(data).decode())
    
    def _builtin_hex_encode(self, *args):
        data = _to_python_value(args[0])
        if isinstance(data, str): data = data.encode()
        return UrmString(data.hex())
    
    def _builtin_hex_decode(self, *args):
        data = _to_python_value(args[0])
        return UrmString(bytes.fromhex(data).decode())
    
    def _builtin_url_encode(self, *args):
        from urllib.parse import quote
        return UrmString(quote(_to_python_value(args[0])))
    
    def _builtin_url_decode(self, *args):
        from urllib.parse import unquote
        return UrmString(unquote(_to_python_value(args[0])))
    
    def _builtin_uuid(self, *args):
        return UrmString(str(uuid.uuid4()))
    
    def _builtin_uuid_v4(self, *args):
        return UrmString(str(uuid.uuid4()))
    
    def _builtin_env_get(self, *args):
        key = _to_python_value(args[0])
        val = os.environ.get(key, "")
        return UrmString(val)
    
    def _builtin_env_set(self, *args):
        key = _to_python_value(args[0])
        val = _to_python_value(args[1])
        os.environ[key] = str(val)
        return URM_NONE
    
    def _builtin_cwd(self, *args):
        return UrmString(os.getcwd())
    
    def _builtin_args(self, *args):
        return UrmArray([UrmString(a) for a in sys.argv])
    
    def _builtin_exec(self, *args):
        cmd = _to_python_value(args[0])
        try:
            import subprocess
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return UrmDict({
                "stdout": UrmString(result.stdout),
                "stderr": UrmString(result.stderr),
                "exit_code": UrmInt(result.returncode),
            })
        except Exception as e:
            return UrmError("ExecError", str(e))
    
    def _builtin_exit(self, *args):
        code = _to_python_value(args[0]) if args else 0
        sys.exit(int(code))
    
    def _builtin_file_exists(self, *args):
        path = _to_python_value(args[0])
        return UrmBool(os.path.exists(path))
    
    def _builtin_file_size(self, *args):
        path = _to_python_value(args[0])
        try:
            return UrmInt(os.path.getsize(path))
        except:
            return UrmInt(-1)
    
    def _builtin_is_dir(self, *args):
        return UrmBool(os.path.isdir(_to_python_value(args[0])))
    
    def _builtin_is_file(self, *args):
        return UrmBool(os.path.isfile(_to_python_value(args[0])))
    
    def _builtin_list_dir(self, *args):
        path = _to_python_value(args[0]) if args else "."
        try:
            return UrmArray([UrmString(f) for f in os.listdir(path)])
        except:
            return UrmArray()
    
    def _builtin_make_dir(self, *args):
        path = _to_python_value(args[0])
        try:
            os.makedirs(path, exist_ok=True)
            return URM_TRUE
        except:
            return URM_FALSE
    
    def _builtin_remove(self, *args):
        path = _to_python_value(args[0])
        try:
            if os.path.isdir(path):
                os.rmdir(path)
            else:
                os.remove(path)
            return URM_TRUE
        except:
            return URM_FALSE
    
    def _builtin_rename(self, *args):
        try:
            os.rename(_to_python_value(args[0]), _to_python_value(args[1]))
            return URM_TRUE
        except:
            return URM_FALSE
    
    def _builtin_copy(self, *args):
        try:
            import shutil
            shutil.copy2(_to_python_value(args[0]), _to_python_value(args[1]))
            return URM_TRUE
        except:
            return URM_FALSE
    
    def _builtin_path_join(self, *args):
        parts = [_to_python_value(a) for a in args]
        return UrmString(os.path.join(*parts))
    
    def _builtin_path_split(self, *args):
        path = _to_python_value(args[0])
        d, f = os.path.split(path)
        return UrmArray([UrmString(d), UrmString(f)])
    
    def _builtin_path_ext(self, *args):
        return UrmString(os.path.splitext(_to_python_value(args[0]))[1])
    
    def _builtin_path_base(self, *args):
        return UrmString(os.path.basename(_to_python_value(args[0])))
    
    def _builtin_path_dir(self, *args):
        return UrmString(os.path.dirname(_to_python_value(args[0])))
    
    def _builtin_panic(self, *args):
        msg = ' '.join(_repr(a) if isinstance(a, UrmObject) else str(a) for a in args)
        raise UrmRuntimeError(msg, "Panic")
    
    def _builtin_error(self, *args):
        msg = _to_python_value(args[0]) if args else ""
        error_type = _to_python_value(args[1]) if len(args) > 1 else "Error"
        return UrmError(error_type, msg)
    
    def _builtin_iterate(self, *args):
        obj = args[0]
        return UrmIterator(obj)
    
    def _builtin_take(self, *args):
        n = _to_python_value(args[0])
        arr = args[1]
        if isinstance(arr, UrmArray):
            return UrmArray(arr.elements[:n])
        return arr
    
    def _builtin_drop(self, *args):
        n = _to_python_value(args[0])
        arr = args[1]
        if isinstance(arr, UrmArray):
            return UrmArray(arr.elements[n:])
        return arr
    
    def _builtin_cycle(self, *args):
        arr = args[0]
        if isinstance(arr, UrmArray):
            return UrmArray(list(itertools.cycle(arr.elements)))
        return arr
    
    def _builtin_count(self, *args):
        start = _to_python_value(args[0]) if args else 0
        step = _to_python_value(args[1]) if len(args) > 1 else 1
        return UrmRange(start, 2**31, step, False)
    
    def _builtin_chain(self, *args):
        result = []
        for a in args:
            if isinstance(a, UrmArray):
                result.extend(a.elements)
        return UrmArray(result)
    
    def _builtin_product(self, *args):
        arrays = [a for a in args if isinstance(a, UrmArray)]
        if not arrays:
            return UrmArray()
        result = []
        for combo in itertools.product(*[a.elements for a in arrays]):
            result.append(UrmArray(list(combo)))
        return UrmArray(result)
    
    def _builtin_permutations(self, *args):
        arr = args[0]
        r = _to_python_value(args[1]) if len(args) > 1 else None
        if isinstance(arr, UrmArray):
            perms = list(itertools.permutations(arr.elements, r))
            return UrmArray([UrmArray(list(p)) for p in perms])
        return UrmArray()
    
    def _builtin_combinations(self, *args):
        arr = args[0]
        r = _to_python_value(args[1])
        if isinstance(arr, UrmArray):
            combos = list(itertools.combinations(arr.elements, r))
            return UrmArray([UrmArray(list(c)) for c in combos])
        return UrmArray()
    
    def _builtin_group_by(self, *args):
        fn = args[0]
        arr = args[1]
        if not isinstance(arr, UrmArray):
            return UrmDict()
        groups = {}
        for e in arr.elements:
            key = self._call_function(fn, [e])
            key_str = _to_hash_key(key)
            if key_str not in groups:
                groups[key_str] = []
            groups[key_str].append(e)
        return UrmDict({k: UrmArray(v) for k, v in groups.items()})
    
    def _builtin_partition(self, *args):
        fn = args[0]
        arr = args[1]
        if not isinstance(arr, UrmArray):
            return UrmArray([UrmArray(), UrmArray()])
        truthy, falsy = [], []
        for e in arr.elements:
            if _is_truthy(self._call_function(fn, [e])):
                truthy.append(e)
            else:
                falsy.append(e)
        return UrmArray([UrmArray(truthy), UrmArray(falsy)])
    
    def _builtin_counter(self, *args):
        arr = args[0]
        if isinstance(arr, UrmArray):
            counts = {}
            for e in arr.elements:
                key = _to_hash_key(e)
                counts[key] = counts.get(key, 0) + 1
            return UrmDict({k: UrmInt(v) for k, v in counts.items()})
        return UrmDict()
    
    def _builtin_memoize(self, *args):
        fn = args[0]
        cache = {}
        def memoized(*inner_args):
            key = tuple(_to_hash_key(a) for a in inner_args)
            if key not in cache:
                cache[key] = self._call_function(fn, list(inner_args))
            return cache[key]
        return UrmBuiltinFn(f"memoized_{_repr(fn)}", memoized, -1)
    
    def _builtin_deep_copy(self, *args):
        import copy
        return copy.deepcopy(args[0])
    
    def _builtin_deep_eq(self, *args):
        return UrmBool(_eq(args[0], args[1]))
    
    def _builtin_pad_left(self, *args):
        s = _to_python_value(args[0])
        width = _to_python_value(args[1])
        fill = _to_python_value(args[2])
        return UrmString(s.rjust(width, fill))
    
    def _builtin_pad_right(self, *args):
        s = _to_python_value(args[0])
        width = _to_python_value(args[1])
        fill = _to_python_value(args[2])
        return UrmString(s.ljust(width, fill))
    
    def _builtin_push(self, *args):
        arr, val = args[0], args[1]
        if isinstance(arr, UrmArray):
            arr.append(val)
        return arr
    
    def _builtin_pop(self, *args):
        arr = args[0]
        if isinstance(arr, UrmArray) and arr.elements:
            return arr.elements.pop()
        return URM_NONE
    
    def _builtin_insert(self, *args):
        arr = args[0]
        idx = _to_python_value(args[1])
        val = args[2]
        if isinstance(arr, UrmArray):
            arr.elements.insert(idx, val)
        return arr
    
    def _builtin_remove_at(self, *args):
        arr = args[0]
        idx = _to_python_value(args[1])
        if isinstance(arr, UrmArray) and 0 <= idx < len(arr.elements):
            return arr.elements.pop(idx)
        return URM_NONE
    
    def _csv_parse(self, args):
        text = _to_python_value(args[0])
        lines = text.strip().split('\n')
        if not lines:
            return UrmArray()
        result = []
        for line in lines:
            fields = [UrmString(f.strip()) for f in line.split(',')]
            result.append(UrmArray(fields))
        return UrmArray(result)
    
    # ═══════════════════════════════════════════════════════════
    # Evaluation
    # ═══════════════════════════════════════════════════════════
    
    def run(self, source: str, file: str = "<repl>"):
        """Parse and execute source code."""
        lexer = Lexer(source, file)
        tokens = lexer.tokenize()
        parser = Parser(tokens, file)
        program = parser.parse()
        return self.execute(program)
    
    def execute(self, program: Program):
        """Execute a parsed program."""
        result = URM_NONE
        for decl in program.declarations:
            self._exec_decl(decl, self.global_env)
        for stmt in program.statements:
            result = self._exec_stmt(stmt, self.global_env)
        return result
    
    def _exec_decl(self, decl: Decl, env: Environment):
        if isinstance(decl, FuncDecl):
            fn = UrmFunction(
                name=decl.name,
                arity=len(decl.params),
                closure_env=env,
                is_async=decl.is_async,
                is_generator=decl.is_generator,
                is_method=decl.is_static,
                param_names=[p.name for p in decl.params],
            )
            fn._decl = decl  # store for later execution
            env.define(decl.name, fn, mutable=False)
        
        elif isinstance(decl, StructDecl):
            struct_def = UrmStructDef(
                name=decl.name,
                fields=[f[0] for f in decl.fields],
                field_types={f[0]: f[1] for f in decl.fields if f[1]},
                field_defaults={f[0]: f[2] for f in decl.fields if f[2]},
                traits=decl.traits,
            )
            for m in decl.methods:
                fn = UrmFunction(
                    name=m.name,
                    arity=len(m.params),
                    closure_env=env,
                    is_method=True,
                    is_static=m.is_static,
                    param_names=[p.name for p in m.params],
                )
                fn._decl = m
                if m.is_static:
                    struct_def.static_methods[m.name] = fn
                else:
                    struct_def.methods[m.name] = fn
            env.define(decl.name, struct_def, mutable=False)
        
        elif isinstance(decl, EnumDecl):
            enum_def = UrmEnumDef(
                name=decl.name,
                variants={v[0]: v[1] for v in decl.variants},
            )
            for m in decl.methods:
                fn = UrmFunction(
                    name=m.name,
                    arity=len(m.params),
                    closure_env=env,
                    is_method=True,
                    param_names=[p.name for p in m.params],
                )
                fn._decl = m
                enum_def.methods[m.name] = fn
            env.define(decl.name, enum_def, mutable=False)
        
        elif isinstance(decl, TraitDecl):
            trait_def = UrmTraitDef(
                name=decl.name,
                method_signatures=[(m.name, len(m.params)) for m in decl.method_sigs],
            )
            env.define(decl.name, trait_def, mutable=False)
        
        elif isinstance(decl, ImplDecl):
            target = decl.target_type
            if env.has(target):
                target_def = env.get(target)
                if isinstance(target_def, UrmStructDef):
                    for m in decl.methods:
                        fn = UrmFunction(
                            name=m.name,
                            arity=len(m.params),
                            closure_env=env,
                            is_method=True,
                            param_names=[p.name for p in m.params],
                        )
                        fn._decl = m
                        target_def.methods[m.name] = fn
            env.define(f"impl_{decl.trait_name}_{decl.target_type}" if decl.trait_name else f"impl_{decl.target_type}",
                      URM_NONE, mutable=False)
        
        elif isinstance(decl, TypeAliasDecl):
            env.define(decl.name, UrmTypeObj(decl.name, decl.target), mutable=False)
        
        elif isinstance(decl, ImportStmt):
            self._exec_import(decl, env)
        
        elif isinstance(decl, ExportStmt):
            pass  # handled at module level
        
        elif isinstance(decl, ConstStmt):
            val = self._eval_expr(decl.value, env)
            env.define(decl.name, val, mutable=False)
    
    def _exec_import(self, decl: ImportStmt, env: Environment):
        module_name = decl.module
        # Try stdlib first
        if module_name in self.stdlib:
            mod = self.stdlib[module_name]
            if decl.names:
                for name in decl.names:
                    if name in mod.exports:
                        env.define(name, mod.exports[name], mutable=False)
            else:
                alias = decl.alias or module_name.split('.')[-1]
                env.define(alias, mod, mutable=False)
            return
        
        # Try file import
        possible_paths = [
            module_name + '.urm',
            module_name.replace('.', '/') + '.urm',
            os.path.join('lib', module_name + '.urm'),
            os.path.join('lib', module_name.replace('.', '/') + '.urm'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        source = f.read()
                    lexer = Lexer(source, path)
                    tokens = lexer.tokenize()
                    parser = Parser(tokens, path)
                    program = parser.parse()
                    
                    mod_env = Environment(parent=self.global_env)
                    for d in program.declarations:
                        self._exec_decl(d, mod_env)
                    for s in program.statements:
                        self._exec_stmt(s, mod_env)
                    
                    mod = UrmModule(name=module_name)
                    mod.exports = dict(mod_env.variables)
                    
                    if decl.names:
                        for name in decl.names:
                            if name in mod_env.variables:
                                env.define(name, mod_env.variables[name], mutable=False)
                    else:
                        alias = decl.alias or module_name.split('.')[-1]
                        env.define(alias, mod, mutable=False)
                    return
                except Exception as e:
                    env.define(module_name.split('.')[-1], UrmError("ImportError", str(e)), mutable=False)
                    return
    
    def _exec_stmt(self, stmt: Stmt, env: Environment):
        if isinstance(stmt, LetStmt):
            val = self._eval_expr(stmt.value, env) if stmt.value else URM_NONE
            env.define(stmt.name, val, mutable=stmt.mutable)
            return val
        
        elif isinstance(stmt, ConstStmt):
            val = self._eval_expr(stmt.value, env)
            env.define(stmt.name, val, mutable=False)
            return val
        
        elif isinstance(stmt, ExprStmt):
            return self._eval_expr(stmt.expr, env)
        
        elif isinstance(stmt, AssignStmt):
            val = self._eval_expr(stmt.value, env)
            self._assign(stmt.target, stmt.op, val, env)
            return val
        
        elif isinstance(stmt, Block):
            block_env = env.child()
            result = URM_NONE
            for s in stmt.statements:
                result = self._exec_stmt(s, block_env)
            return result
        
        elif isinstance(stmt, IfStmt):
            cond = self._eval_expr(stmt.condition, env)
            if _is_truthy(cond):
                return self._exec_block(stmt.then_block, env)
            for elif_cond, elif_body in stmt.elif_clauses:
                if _is_truthy(self._eval_expr(elif_cond, env)):
                    return self._exec_block(elif_body, env)
            if stmt.else_block:
                return self._exec_block(stmt.else_block, env)
            return URM_NONE
        
        elif isinstance(stmt, WhileStmt):
            result = URM_NONE
            while _is_truthy(self._eval_expr(stmt.condition, env)):
                try:
                    result = self._exec_block(stmt.body, env)
                except _BreakException as e:
                    result = e.value
                    break
                except _ContinueException:
                    continue
            return result
        
        elif isinstance(stmt, ForInStmt):
            iterable = self._eval_expr(stmt.iterable, env)
            result = URM_NONE
            items = self._to_iterable(iterable)
            for item in items:
                loop_env = env.child()
                loop_env.define(stmt.name, item, mutable=False)
                try:
                    result = self._exec_block(stmt.body, loop_env)
                except _BreakException as e:
                    result = e.value
                    break
                except _ContinueException:
                    continue
            return result
        
        elif isinstance(stmt, LoopStmt):
            result = URM_NONE
            while True:
                try:
                    result = self._exec_block(stmt.body, env)
                except _BreakException as e:
                    result = e.value
                    break
                except _ContinueException:
                    continue
            return result
        
        elif isinstance(stmt, BreakStmt):
            raise _BreakException(self._eval_expr(stmt.value, env) if stmt.value else URM_NONE)
        
        elif isinstance(stmt, ContinueStmt):
            raise _ContinueException()
        
        elif isinstance(stmt, ReturnStmt):
            val = self._eval_expr(stmt.value, env) if stmt.value else URM_NONE
            raise _ReturnException(val)
        
        elif isinstance(stmt, YieldStmt):
            val = self._eval_expr(stmt.value, env) if stmt.value else URM_NONE
            return val
        
        elif isinstance(stmt, ThrowStmt):
            err = self._eval_expr(stmt.error, env)
            if isinstance(err, UrmString):
                raise UrmRuntimeError(err.value)
            elif isinstance(err, UrmError):
                raise UrmRuntimeError(err.message, err.error_type)
            raise UrmRuntimeError(_repr(err))
        
        elif isinstance(stmt, DeferStmt):
            # Defer: execute at end of scope (simplified: execute now in reverse)
            # For proper defer, we'd need scope tracking
            pass
        
        elif isinstance(stmt, AssertStmt):
            cond = self._eval_expr(stmt.condition, env)
            if not _is_truthy(cond):
                msg = _repr(self._eval_expr(stmt.message, env)) if stmt.message else "Assertion failed"
                raise UrmRuntimeError(msg, "AssertionError")
            return URM_NONE
        
        elif isinstance(stmt, MatchStmt):
            subject = self._eval_expr(stmt.subject, env)
            for patterns, guard, body in stmt.arms:
                match = False
                bindings = {}
                for pattern in patterns:
                    m, b = self._match_pattern(pattern, subject, env)
                    if m:
                        match = True
                        bindings.update(b)
                        break
                if match:
                    if guard:
                        guard_env = env.child()
                        for k, v in bindings.items():
                            guard_env.define(k, v, mutable=False)
                        if not _is_truthy(self._eval_expr(guard, guard_env)):
                            continue
                    match_env = env.child()
                    for k, v in bindings.items():
                        match_env.define(k, v, mutable=False)
                    return self._exec_block(body, match_env)
            return URM_NONE
        
        elif isinstance(stmt, TryCatchStmt):
            try:
                return self._exec_block(stmt.try_block, env)
            except UrmRuntimeError as e:
                for error_type, var_name, catch_body in stmt.catches:
                    if not error_type or error_type == e.error_type:
                        catch_env = env.child()
                        if var_name:
                            catch_env.define(var_name, UrmError(e.error_type, e.message), mutable=False)
                        return self._exec_block(catch_body, catch_env)
                raise
            except _ReturnException:
                raise
            except Exception as e:
                for error_type, var_name, catch_body in stmt.catches:
                    if not error_type:
                        catch_env = env.child()
                        if var_name:
                            catch_env.define(var_name, UrmError("Error", str(e)), mutable=False)
                        return self._exec_block(catch_body, catch_env)
                raise
            finally:
                if stmt.finally_block:
                    self._exec_block(stmt.finally_block, env)
        
        elif isinstance(stmt, ImportStmt):
            self._exec_import(stmt, env)
            return URM_NONE
        
        elif isinstance(stmt, UsingStmt):
            if stmt.module in self.stdlib:
                mod = self.stdlib[stmt.module]
                for name, val in mod.exports.items():
                    if not env.has(name):
                        env.define(name, val, mutable=False)
            return URM_NONE
        
        return URM_NONE
    
    def _exec_block(self, block, env):
        if isinstance(block, Block):
            return self._exec_stmt(block, env)
        if isinstance(block, Stmt):
            return self._exec_stmt(block, env)
        return URM_NONE
    
    def _to_iterable(self, obj):
        """Convert a UrmObject to a list of items for iteration."""
        if isinstance(obj, UrmArray):
            return obj.elements
        if isinstance(obj, UrmRange):
            return [UrmInt(v) for v in obj.to_list()]
        if isinstance(obj, UrmDict):
            return [_from_hash_key(k) for k in obj.pairs.keys()]
        if isinstance(obj, UrmString):
            return [UrmString(c) for c in obj.value]
        if isinstance(obj, UrmTuple):
            return obj.elements
        if isinstance(obj, UrmSet):
            return [_from_hash_key(e) for e in obj.elements]
        return [obj]
    
    def _match_pattern(self, pattern, value, env):
        """Try to match a pattern against a value. Returns (matched, bindings)."""
        ptype = pattern[0]
        
        if ptype == 'wildcard':
            return True, {}
        
        if ptype == 'literal':
            expected = pattern[1]
            if isinstance(value, UrmInt) and isinstance(expected, int):
                return value.value == expected, {}
            if isinstance(value, UrmFloat) and isinstance(expected, float):
                return value.value == expected, {}
            if isinstance(value, UrmString) and isinstance(expected, str):
                return value.value == expected, {}
            if isinstance(value, UrmBool) and isinstance(expected, bool):
                return value.value == expected, {}
            if isinstance(value, UrmNone) and expected is None:
                return True, {}
            return False, {}
        
        if ptype == 'binding':
            name = pattern[1]
            return True, {name: value}
        
        if ptype == 'enum':
            enum_name, variant_name, data_pats = pattern[1], pattern[2], pattern[3]
            if isinstance(value, UrmEnumVariant):
                if value.enum_name == enum_name and value.variant_name == variant_name:
                    bindings = {}
                    for i, dp in enumerate(data_pats):
                        if i < len(value.data):
                            m, b = self._match_pattern(dp, value.data[i], env)
                            if not m:
                                return False, {}
                            bindings.update(b)
                    return True, bindings
            return False, {}
        
        if ptype == 'destructure':
            name, field_pats = pattern[1], pattern[2]
            if isinstance(value, UrmStructInstance) and value.struct_def and value.struct_def.name == name:
                bindings = {}
                for i, fp in enumerate(field_pats):
                    fields = list(value.fields.values())
                    if i < len(fields):
                        m, b = self._match_pattern(fp, fields[i], env)
                        if not m:
                            return False, {}
                        bindings.update(b)
                return True, bindings
            if isinstance(value, UrmArray) or isinstance(value, UrmTuple):
                items = value.elements if hasattr(value, 'elements') else []
                bindings = {}
                for i, fp in enumerate(field_pats):
                    if i < len(items):
                        m, b = self._match_pattern(fp, items[i], env)
                        if not m:
                            return False, {}
                        bindings.update(b)
                return True, bindings
            return False, {}
        
        if ptype == 'type_bind':
            name, type_name = pattern[1], pattern[2]
            if isinstance(value, UrmObject) and value.urm_type_name() == type_name:
                return True, {name: value}
            return False, {}
        
        return False, {}
    
    def _assign(self, target, op, value, env):
        """Handle assignment to various target types."""
        if isinstance(target, Identifier):
            if op != "=":
                old = env.get(target.name)
                value = self._compound_assign(old, op, value)
            env.set(target.name, value)
        
        elif isinstance(target, MemberAccess):
            obj = self._eval_expr(target.object, env)
            if isinstance(obj, UrmStructInstance):
                obj.fields[target.member] = value
            elif isinstance(obj, UrmDict):
                obj.set(UrmString(target.member), value)
        
        elif isinstance(target, IndexAccess):
            obj = self._eval_expr(target.object, env)
            idx = self._eval_expr(target.index, env)
            if isinstance(obj, UrmArray):
                obj.set(idx, value)
            elif isinstance(obj, UrmDict):
                obj.set(idx, value)
    
    def _compound_assign(self, old, op, value):
        ops = {
            "+=": lambda a, b: a + b,
            "-=": lambda a, b: a - b,
            "*=": lambda a, b: a * b,
            "/=": lambda a, b: a / b if isinstance(a, float) or isinstance(b, float) else a // b,
            "%=": lambda a, b: a % b,
            "**=": lambda a, b: a ** b,
        }
        if isinstance(old, UrmInt) and isinstance(value, UrmInt):
            result = ops.get(op, lambda a, b: b)(old.value, value.value)
            return UrmInt(int(result))
        if isinstance(old, (UrmInt, UrmFloat)) and isinstance(value, (UrmInt, UrmFloat)):
            ov = old.value if isinstance(old, (UrmInt, UrmFloat)) else 0
            vv = value.value if isinstance(value, (UrmInt, UrmFloat)) else 0
            result = ops.get(op, lambda a, b: b)(ov, vv)
            return UrmFloat(float(result))
        if isinstance(old, UrmString) and op == "+=" and isinstance(value, UrmString):
            return UrmString(old.value + value.value)
        return value
    
    # ═══════════════════════════════════════════════════════════
    # Expression Evaluation
    # ═══════════════════════════════════════════════════════════
    
    def _eval_expr(self, expr: Expr, env: Environment):
        if isinstance(expr, IntLiteral):
            return UrmInt(expr.value)
        if isinstance(expr, FloatLiteral):
            return UrmFloat(expr.value)
        if isinstance(expr, StringLiteral):
            return UrmString(expr.value)
        if isinstance(expr, InterpolatedString):
            result = []
            for part_type, part_val in expr.parts:
                if part_type == 'str':
                    result.append(part_val)
                elif part_type == 'expr':
                    try:
                        val = self.run(part_val)
                        result.append(_repr(val) if isinstance(val, UrmObject) else str(val))
                    except:
                        result.append(part_val)
            return UrmString(''.join(result))
        if isinstance(expr, BoolLiteral):
            return URM_TRUE if expr.value else URM_FALSE
        if isinstance(expr, NoneLiteral):
            return URM_NONE
        if isinstance(expr, Identifier):
            if expr.name == "_":
                return URM_NONE
            return env.get(expr.name)
        if isinstance(expr, SelfExpr):
            return env.get("self")
        if isinstance(expr, SuperExpr):
            return env.get("super")
        
        if isinstance(expr, ArrayLiteral):
            elements = [self._eval_expr(e, env) for e in expr.elements]
            return UrmArray(elements)
        
        if isinstance(expr, DictLiteral):
            pairs = {}
            for k, v in expr.pairs:
                key = self._eval_expr(k, env)
                val = self._eval_expr(v, env)
                pairs[_to_hash_key(key)] = val
            return UrmDict(pairs)
        
        if isinstance(expr, TupleLiteral):
            elements = [self._eval_expr(e, env) for e in expr.elements]
            return UrmTuple(elements)
        
        if isinstance(expr, SetLiteral):
            elements = set()
            for e in expr.elements:
                val = self._eval_expr(e, env)
                elements.add(_to_hash_key(val))
            return UrmSet(elements)
        
        if isinstance(expr, RangeLiteral):
            start = _to_python_value(self._eval_expr(expr.start, env))
            end = _to_python_value(self._eval_expr(expr.end, env))
            step = _to_python_value(self._eval_expr(expr.step, env)) if expr.step else 1
            return UrmRange(start, end, step, expr.inclusive)
        
        if isinstance(expr, BinaryOp):
            return self._eval_binary(expr, env)
        
        if isinstance(expr, UnaryOp):
            return self._eval_unary(expr, env)
        
        if isinstance(expr, Comparison):
            return self._eval_comparison(expr, env)
        
        if isinstance(expr, LogicalOp):
            left = self._eval_expr(expr.left, env)
            if expr.op == "and":
                return left if not _is_truthy(left) else self._eval_expr(expr.right, env)
            if expr.op == "or":
                return left if _is_truthy(left) else self._eval_expr(expr.right, env)
        
        if isinstance(expr, TernaryExpr):
            cond = self._eval_expr(expr.condition, env)
            if _is_truthy(cond):
                return self._eval_expr(expr.true_expr, env)
            return self._eval_expr(expr.false_expr, env)
        
        if isinstance(expr, NullCoalesce):
            left = self._eval_expr(expr.left, env)
            if isinstance(left, UrmNone):
                return self._eval_expr(expr.right, env)
            return left
        
        if isinstance(expr, ElvisExpr):
            cond = self._eval_expr(expr.condition, env)
            if _is_truthy(cond):
                return cond
            return self._eval_expr(expr.default, env)
        
        if isinstance(expr, AssignExpr):
            val = self._eval_expr(expr.value, env)
            self._assign(expr.target, expr.op, val, env)
            return val
        
        if isinstance(expr, CallExpr):
            return self._eval_call(expr, env)
        
        if isinstance(expr, MethodCallExpr):
            return self._eval_method_call(expr, env)
        
        if isinstance(expr, MemberAccess):
            return self._eval_member(expr, env)
        
        if isinstance(expr, IndexAccess):
            return self._eval_index(expr, env)
        
        if isinstance(expr, SliceExpr):
            return self._eval_slice(expr, env)
        
        if isinstance(expr, PipeExpr):
            left = self._eval_expr(expr.left, env)
            fn = self._eval_expr(expr.right, env)
            return self._call_function(fn, [left])
        
        if isinstance(expr, ComposeExpr):
            f = self._eval_expr(expr.left, env)
            g = self._eval_expr(expr.right, env)
            def composed(*args):
                return self._call_function(f, [self._call_function(g, list(args))])
            return UrmBuiltinFn("composed", composed, -1)
        
        if isinstance(expr, LambdaExpr):
            fn = UrmFunction(
                name="<lambda>",
                arity=len(expr.params),
                closure_env=env,
                is_async=expr.is_async,
                param_names=[p.name for p in expr.params],
            )
            fn._lambda_body = expr.body
            fn._lambda_params = expr.params
            return fn
        
        if isinstance(expr, SpawnExpr):
            fn = self._eval_expr(expr.expr, env)
            future = UrmFuture()
            def run():
                try:
                    if isinstance(fn, UrmFunction):
                        result = self._call_function(fn, [])
                    elif isinstance(fn, UrmBuiltinFn):
                        result = fn.fn()
                    else:
                        result = fn
                    future.set_result(result)
                except Exception as e:
                    future.set_error(UrmRuntimeError(str(e)))
            t = threading.Thread(target=run, daemon=True)
            future._thread = t
            t.start()
            return future
        
        if isinstance(expr, AwaitExpr):
            val = self._eval_expr(expr.expr, env)
            if isinstance(val, UrmFuture):
                return val.get_value()
            return val
        
        if isinstance(expr, YieldExpr):
            return self._eval_expr(expr.value, env) if expr.value else URM_NONE
        
        if isinstance(expr, SpreadExpr):
            val = self._eval_expr(expr.expr, env)
            if isinstance(val, UrmArray):
                return val  # Spread handled in collection literals
            return val
        
        if isinstance(expr, IsExpr):
            left = self._eval_expr(expr.left, env)
            type_name = expr.right.name if isinstance(expr.right, SimpleType) else str(expr.right)
            if isinstance(left, UrmObject):
                return UrmBool(left.urm_type_name() == type_name)
            return URM_FALSE
        
        if isinstance(expr, EnumVariantAccess):
            try:
                enum_def = env.get(expr.enum_name)
                if isinstance(enum_def, UrmEnumDef):
                    return UrmEnumVariant(enum_name=expr.enum_name, variant_name=expr.variant_name)
            except:
                pass
            return UrmEnumVariant(enum_name=expr.enum_name, variant_name=expr.variant_name)
        
        if isinstance(expr, NewExpr):
            type_def = env.get(expr.type_name)
            if isinstance(type_def, UrmStructDef):
                args = [self._eval_expr(a, env) for a in expr.args]
                instance = UrmStructInstance(struct_def=type_def)
                for i, field_name in enumerate(type_def.fields):
                    if i < len(args):
                        instance.fields[field_name] = args[i]
                    elif field_name in type_def.field_defaults:
                        instance.fields[field_name] = self._eval_expr(type_def.field_defaults[field_name], env)
                return instance
            return URM_NONE
        
        if isinstance(expr, RegexLiteral):
            return UrmRegex(expr.pattern)
        
        if isinstance(expr, TypeCastExpr):
            val = self._eval_expr(expr.expr, env)
            target = expr.target_type
            if isinstance(target, SimpleType):
                if target.name == "int":
                    return self._builtin_int(val)
                if target.name == "float":
                    return self._builtin_float(val)
                if target.name == "str":
                    return self._builtin_str(val)
                if target.name == "bool":
                    return self._builtin_bool(val)
            return val
        
        if isinstance(expr, GroupedExpr):
            return self._eval_expr(expr.expr, env)
        
        if isinstance(expr, ListComp):
            result = []
            iterable = self._eval_expr(expr.iter_expr, env)
            for item in self._to_iterable(iterable):
                comp_env = env.child()
                comp_env.define(expr.iter_var, item, mutable=False)
                if expr.condition and not _is_truthy(self._eval_expr(expr.condition, comp_env)):
                    continue
                result.append(self._eval_expr(expr.result_expr, comp_env))
            return UrmArray(result)
        
        if isinstance(expr, DictComp):
            result = {}
            iterable = self._eval_expr(expr.iter_expr, env)
            for item in self._to_iterable(iterable):
                comp_env = env.child()
                comp_env.define(expr.iter_var, item, mutable=False)
                if expr.condition and not _is_truthy(self._eval_expr(expr.condition, comp_env)):
                    continue
                k = self._eval_expr(expr.key_expr, comp_env)
                v = self._eval_expr(expr.value_expr, comp_env)
                result[_to_hash_key(k)] = v
            return UrmDict(result)
        
        if isinstance(expr, SetComp):
            result = set()
            iterable = self._eval_expr(expr.iter_expr, env)
            for item in self._to_iterable(iterable):
                comp_env = env.child()
                comp_env.define(expr.iter_var, item, mutable=False)
                if expr.condition and not _is_truthy(self._eval_expr(expr.condition, comp_env)):
                    continue
                result.add(_to_hash_key(self._eval_expr(expr.result_expr, comp_env)))
            return UrmSet(result)
        
        return URM_NONE
    
    def _eval_binary(self, expr: BinaryOp, env: Environment):
        left = self._eval_expr(expr.left, env)
        
        # Short-circuit for string concatenation
        if expr.op == "+" and isinstance(left, UrmString):
            right = self._eval_expr(expr.right, env)
            if isinstance(right, UrmString):
                return UrmString(left.value + right.value)
            return UrmString(left.value + _repr(right))
        
        right = self._eval_expr(expr.right, env)
        op = expr.op
        
        # Arithmetic
        if op == "+": return self._add(left, right)
        if op == "-": return self._sub(left, right)
        if op == "*": return self._mul(left, right)
        if op == "/":
            if isinstance(right, UrmInt) and right.value == 0:
                raise UrmRuntimeError("Division by zero")
            if isinstance(right, UrmFloat) and right.value == 0.0:
                raise UrmRuntimeError("Division by zero")
            return self._div(left, right)
        if op == "//": return self._floor_div(left, right)
        if op == "%": return self._mod(left, right)
        if op == "**": return self._pow(left, right)
        
        # Bitwise
        if op == "&": return left & right
        if op == "|": return left | right
        if op == "^": return left ^ right
        if op == "<<": return left << right
        if op == ">>": return left >> right
        
        # Comparison
        if op == "==": return UrmBool(_eq(left, right))
        if op == "!=": return UrmBool(not _eq(left, right))
        if op == "<": return UrmBool(self._compare(left, right) < 0)
        if op == "<=": return UrmBool(self._compare(left, right) <= 0)
        if op == ">": return UrmBool(self._compare(left, right) > 0)
        if op == ">=": return UrmBool(self._compare(left, right) >= 0)
        if op == "<=>": return UrmInt(self._compare(left, right))
        
        raise UrmRuntimeError(f"Unknown operator: {op}")
    
    def _eval_unary(self, expr: UnaryOp, env: Environment):
        operand = self._eval_expr(expr.operand, env)
        op = expr.op
        if op == "-": 
            if isinstance(operand, UrmInt): return UrmInt(-operand.value)
            if isinstance(operand, UrmFloat): return UrmFloat(-operand.value)
        if op == "not" or op == "!":
            return URM_FALSE if _is_truthy(operand) else URM_TRUE
        if op == "~":
            if isinstance(operand, UrmInt): return UrmInt(~operand.value)
        return operand
    
    def _eval_comparison(self, expr: Comparison, env: Environment):
        left = self._eval_expr(expr.left, env)
        for op, right_expr in expr.ops:
            right = self._eval_expr(right_expr, env)
            if op == "==" and not _eq(left, right): return URM_FALSE
            if op == "!=" and _eq(left, right): return URM_FALSE
            if op == "<" and not self._compare(left, right) < 0: return URM_FALSE
            if op == "<=" and not self._compare(left, right) <= 0: return URM_FALSE
            if op == ">" and not self._compare(left, right) > 0: return URM_FALSE
            if op == ">=" and not self._compare(left, right) >= 0: return URM_FALSE
            left = right
        return URM_TRUE
    
    def _eval_call(self, expr: CallExpr, env: Environment):
        callee = self._eval_expr(expr.callee, env)
        args = [self._eval_expr(a, env) for a in expr.args]
        
        # Handle keyword arguments
        for k, v in expr.kwargs.items():
            args.append(self._eval_expr(v, env))
        
        return self._call_function(callee, args)
    
    def _call_function(self, fn, args):
        """Call a Urmom Lang function with arguments."""
        if isinstance(fn, UrmBuiltinFn):
            try:
                return fn.fn(*args)
            except Exception as e:
                raise UrmRuntimeError(f"Error in builtin {fn.name}: {e}")
        
        if isinstance(fn, UrmFunction):
            if hasattr(fn, '_decl') and fn._decl:
                decl = fn._decl
                call_env = Environment(parent=fn.closure_env or self.global_env)
                
                # Bind parameters
                for i, param in enumerate(decl.params):
                    if i < len(args):
                        call_env.define(param.name, args[i], mutable=param.is_mut)
                    elif param.default:
                        call_env.define(param.name, self._eval_expr(param.default, call_env), mutable=param.is_mut)
                    else:
                        call_env.define(param.name, URM_NONE, mutable=param.is_mut)
                
                # Add 'self' if method
                if fn.is_method and args:
                    call_env.define("self", args[0], mutable=False)
                
                # Execute body
                try:
                    result = self._exec_block(decl.body, call_env)
                except _ReturnException as e:
                    result = e.value
                
                return result
            
            if hasattr(fn, '_lambda_body') and fn._lambda_body:
                body = fn._lambda_body
                call_env = Environment(parent=fn.closure_env or self.global_env)
                
                params = fn._lambda_params if hasattr(fn, '_lambda_params') else []
                for i, param in enumerate(params):
                    if i < len(args):
                        call_env.define(param.name, args[i], mutable=param.is_mut)
                    elif param.default:
                        call_env.define(param.name, self._eval_expr(param.default, call_env), mutable=param.is_mut)
                    else:
                        call_env.define(param.name, URM_NONE, mutable=param.is_mut)
                
                if isinstance(body, Block):
                    try:
                        result = self._exec_block(body, call_env)
                    except _ReturnException as e:
                        result = e.value
                    return result
                else:
                    return self._eval_expr(body, call_env)
        
        if isinstance(fn, UrmStructDef):
            # Calling a struct = creating an instance
            instance = UrmStructInstance(struct_def=fn)
            for i, field_name in enumerate(fn.fields):
                if i < len(args):
                    instance.fields[field_name] = args[i]
                elif field_name in fn.field_defaults:
                    instance.fields[field_name] = self._eval_expr(fn.field_defaults[field_name], self.global_env)
            return instance
        
        if isinstance(fn, UrmEnumDef):
            # Calling an enum with variant name
            if args and isinstance(args[0], UrmString):
                return UrmEnumVariant(enum_name=fn.name, variant_name=args[0].value, 
                                     data=args[1:])
            return UrmEnumVariant(enum_name=fn.name, variant_name="", data=args)
        
        raise UrmRuntimeError(f"Cannot call {_repr(fn)}")
    
    def _eval_method_call(self, expr: MethodCallExpr, env: Environment):
        obj = self._eval_expr(expr.object, env)
        
        if expr.null_safe and isinstance(obj, UrmNone):
            return URM_NONE
        
        args = [self._eval_expr(a, env) for a in expr.args]
        method_name = expr.method
        
        # Built-in methods on objects
        result = self._try_object_method(obj, method_name, args)
        if result is not self._METHOD_NOT_FOUND:
            return result
        
        # Struct instance method
        if isinstance(obj, UrmStructInstance) and obj.struct_def:
            if method_name in obj.struct_def.methods:
                fn = obj.struct_def.methods[method_name]
                return self._call_function(fn, [obj] + args)
            # Check trait methods via impl
            for trait_name in obj.struct_def.traits:
                try:
                    impl_key = f"impl_{trait_name}_{obj.struct_def.name}"
                    if env.has(impl_key):
                        pass  # impl already applied to struct
                except:
                    pass
        
        # Enum method
        if isinstance(obj, UrmEnumDef):
            if method_name in obj.methods:
                fn = obj.methods[method_name]
                return self._call_function(fn, [obj] + args)
        
        # Struct static method
        if isinstance(obj, UrmStructDef):
            if method_name in obj.static_methods:
                fn = obj.static_methods[method_name]
                return self._call_function(fn, args)
        
        raise UrmRuntimeError(f"No method '{method_name}' on {_repr(obj)}")
    
    _METHOD_NOT_FOUND = object()
    
    def _try_object_method(self, obj, method, args):
        """Try to call a built-in method on a UrmObject."""
        if isinstance(obj, UrmArray):
            if method == "push": obj.append(args[0] if args else URM_NONE); return obj
            if method == "pop": return obj.elements.pop() if obj.elements else URM_NONE
            if method == "map": return obj.map(args[0]) if args else obj
            if method == "filter": return obj.filter(args[0]) if args else obj
            if method == "reduce": return obj.reduce(args[0], args[1] if len(args) > 1 else None)
            if method == "sort": obj.sort(args[0] if args else None); return obj
            if method == "reverse": obj.reverse(); return obj
            if method == "len": return UrmInt(obj.length())
            if method == "contains": return obj.contains(args[0]) if args else URM_FALSE
            if method == "find": return obj.find(args[0]) if args else URM_NONE
            if method == "flat": return obj.flat(_to_python_value(args[0]) if args else 1)
            if method == "unique": return obj.unique()
            if method == "join": return UrmString(_to_python_value(args[0]).join(_repr(e) for e in obj.elements)) if args else UrmString("")
            if method == "slice": return obj.slice(args[0], args[1] if len(args) > 1 else None)
            if method == "first": return obj.elements[0] if obj.elements else URM_NONE
            if method == "last": return obj.elements[-1] if obj.elements else URM_NONE
            if method == "is_empty": return UrmBool(len(obj.elements) == 0)
            if method == "chunk": return obj.chunk(args[0]) if args else UrmArray()
        
        if isinstance(obj, UrmString):
            if method == "len": return UrmInt(len(obj.value))
            if method == "upper": return UrmString(obj.value.upper())
            if method == "lower": return UrmString(obj.value.lower())
            if method == "trim": return UrmString(obj.value.strip())
            if method == "split": return UrmArray([UrmString(p) for p in obj.value.split(_to_python_value(args[0]) if args else None)])
            if method == "contains": return UrmBool(_to_python_value(args[0]) in obj.value) if args else URM_FALSE
            if method == "starts_with": return UrmBool(obj.value.startswith(_to_python_value(args[0]))) if args else URM_FALSE
            if method == "ends_with": return UrmBool(obj.value.endswith(_to_python_value(args[0]))) if args else URM_FALSE
            if method == "replace": return UrmString(obj.value.replace(_to_python_value(args[0]), _to_python_value(args[1]))) if len(args) >= 2 else obj
            if method == "reverse": return UrmString(obj.value[::-1])
            if method == "repeat": return UrmString(obj.value * _to_python_value(args[0])) if args else obj
            if method == "is_empty": return UrmBool(len(obj.value) == 0)
            if method == "chars": return UrmArray([UrmString(c) for c in obj.value])
            if method == "bytes": return UrmBytes(obj.value.encode('utf-8'))
        
        if isinstance(obj, UrmDict):
            if method == "get": return obj.get(args[0]) if args else URM_NONE
            if method == "set": obj.set(args[0], args[1]) if len(args) >= 2 else None; return obj
            if method == "has": return UrmBool(obj.has(args[0])) if args else URM_FALSE
            if method == "remove": obj.remove(args[0]) if args else None; return obj
            if method == "keys": return obj.keys()
            if method == "values": return obj.values()
            if method == "items": return obj.items()
            if method == "len": return UrmInt(obj.length())
            if method == "merge": return obj.merge(args[0]) if args else obj
            if method == "is_empty": return UrmBool(len(obj.pairs) == 0)
        
        if isinstance(obj, UrmChannel):
            if method == "send": obj.send(args[0]) if args else None; return URM_NONE
            if method == "receive": return obj.receive()
            if method == "close": obj.close(); return URM_NONE
            if method == "is_closed": return UrmBool(obj.is_closed())
            if method == "capacity": return UrmInt(obj.capacity)
        
        if isinstance(obj, UrmFuture):
            if method == "get_value": return obj.get_value()
            if method == "is_ready": return UrmBool(obj.is_ready())
            if method == "value":
                if obj.is_ready(): return obj._result
                return obj.get_value()
        
        if isinstance(obj, UrmStructInstance):
            if method in obj.fields:
                fn = obj.fields[method]
                if isinstance(fn, (UrmFunction, UrmBuiltinFn)):
                    return self._call_function(fn, args)
                return fn
        
        if isinstance(obj, UrmRegex):
            if method == "match": 
                m = obj.match(_to_python_value(args[0])) if args else None
                if m: return UrmArray([UrmString(m.group(0))] + [UrmString(g) for g in m.groups()])
                return URM_NONE
            if method == "search":
                m = obj.search(_to_python_value(args[0])) if args else None
                if m: return UrmArray([UrmString(m.group(0))] + [UrmString(g) for g in m.groups()])
                return URM_NONE
            if method == "find_all":
                return UrmArray([UrmString(m) for m in obj.find_all(_to_python_value(args[0]))]) if args else UrmArray()
            if method == "replace":
                return UrmString(obj.replace(_to_python_value(args[0]), _to_python_value(args[1]))) if len(args) >= 2 else UrmString("")
            if method == "split":
                return UrmArray([UrmString(p) for p in obj.split(_to_python_value(args[0]))]) if args else UrmArray()
        
        if isinstance(obj, UrmMutex):
            if method == "lock": obj.acquire(); return URM_NONE
            if method == "unlock": obj.release(); return URM_NONE
        
        if isinstance(obj, UrmModule):
            if method in obj.exports:
                return obj.exports[method]
        
        return self._METHOD_NOT_FOUND
    
    def _eval_member(self, expr: MemberAccess, env: Environment):
        obj = self._eval_expr(expr.object, env)
        
        if expr.null_safe and isinstance(obj, UrmNone):
            return URM_NONE
        
        member = expr.member
        
        # Struct instance field
        if isinstance(obj, UrmStructInstance):
            if member in obj.fields:
                return obj.fields[member]
        
        # Struct definition
        if isinstance(obj, UrmStructDef):
            if member in obj.static_methods:
                return obj.static_methods[member]
            if member in obj.methods:
                return obj.methods[member]
        
        # Enum definition
        if isinstance(obj, UrmEnumDef):
            if member in obj.variants:
                return UrmEnumVariant(enum_name=obj.name, variant_name=member)
            if member in obj.methods:
                return obj.methods[member]
        
        # Module
        if isinstance(obj, UrmModule):
            if member in obj.exports:
                return obj.exports[member]
        
        # Dict key access
        if isinstance(obj, UrmDict):
            key = UrmString(member)
            if obj.has(key):
                return obj.get(key)
        
        # Array/string/dict properties
        if isinstance(obj, UrmArray):
            if member == "length" or member == "len": return UrmInt(obj.length())
            if member == "first": return obj.elements[0] if obj.elements else URM_NONE
            if member == "last": return obj.elements[-1] if obj.elements else URM_NONE
            if member == "is_empty": return UrmBool(len(obj.elements) == 0)
        
        if isinstance(obj, UrmString):
            if member == "length" or member == "len": return UrmInt(len(obj.value))
            if member == "is_empty": return UrmBool(len(obj.value) == 0)
        
        if isinstance(obj, UrmDict):
            if member == "length" or member == "len": return UrmInt(obj.length())
            if member == "is_empty": return UrmBool(len(obj.pairs) == 0)
        
        # Type name
        if isinstance(obj, UrmObject):
            if member == "type": return UrmString(obj.urm_type_name())
        
        return URM_NONE
    
    def _eval_index(self, expr: IndexAccess, env: Environment):
        obj = self._eval_expr(expr.object, env)
        idx = self._eval_expr(expr.index, env)
        
        if expr.null_safe and isinstance(obj, UrmNone):
            return URM_NONE
        
        if isinstance(obj, UrmArray) and isinstance(idx, UrmInt):
            if -len(obj.elements) <= idx.value < len(obj.elements):
                return obj.elements[idx.value]
            return URM_NONE
        
        if isinstance(obj, UrmTuple) and isinstance(idx, UrmInt):
            if -len(obj.elements) <= idx.value < len(obj.elements):
                return obj.elements[idx.value]
            return URM_NONE
        
        if isinstance(obj, UrmString) and isinstance(idx, UrmInt):
            if -len(obj.value) <= idx.value < len(obj.value):
                return UrmString(obj.value[idx.value])
            return URM_NONE
        
        if isinstance(obj, UrmDict):
            return obj.get(idx)
        
        if isinstance(obj, UrmBytes) and isinstance(idx, UrmInt):
            if 0 <= idx.value < len(obj.data):
                return UrmInt(obj.data[idx.value])
            return URM_NONE
        
        return URM_NONE
    
    def _eval_slice(self, expr: SliceExpr, env: Environment):
        obj = self._eval_expr(expr.object, env)
        start = _to_python_value(self._eval_expr(expr.start, env)) if expr.start else None
        end = _to_python_value(self._eval_expr(expr.end, env)) if expr.end else None
        step = _to_python_value(self._eval_expr(expr.step, env)) if expr.step else None
        
        if isinstance(obj, UrmArray):
            return UrmArray(obj.elements[start:end:step])
        if isinstance(obj, UrmString):
            return UrmString(obj.value[start:end:step])
        if isinstance(obj, UrmTuple):
            return UrmTuple(obj.elements[start:end:step])
        
        return URM_NONE
    
    # Arithmetic helpers
    def _add(self, a, b):
        if isinstance(a, UrmInt) and isinstance(b, UrmInt): return UrmInt(a.value + b.value)
        if isinstance(a, UrmFloat) or isinstance(b, UrmFloat): return UrmFloat((a.value if isinstance(a, (UrmInt,UrmFloat)) else 0) + (b.value if isinstance(b, (UrmInt,UrmFloat)) else 0))
        if isinstance(a, UrmString) and isinstance(b, UrmString): return UrmString(a.value + b.value)
        if isinstance(a, UrmArray) and isinstance(b, UrmArray): return UrmArray(a.elements + b.elements)
        raise UrmRuntimeError(f"Cannot add {_repr(a)} and {_repr(b)}")
    
    def _sub(self, a, b):
        if isinstance(a, UrmInt) and isinstance(b, UrmInt): return UrmInt(a.value - b.value)
        if isinstance(a, (UrmInt,UrmFloat)) or isinstance(b, (UrmInt,UrmFloat)): return UrmFloat((a.value if isinstance(a,(UrmInt,UrmFloat)) else 0) - (b.value if isinstance(b,(UrmInt,UrmFloat)) else 0))
        raise UrmRuntimeError(f"Cannot subtract {_repr(a)} and {_repr(b)}")
    
    def _mul(self, a, b):
        if isinstance(a, UrmInt) and isinstance(b, UrmInt): return UrmInt(a.value * b.value)
        if isinstance(a, (UrmInt,UrmFloat)) or isinstance(b, (UrmInt,UrmFloat)): return UrmFloat((a.value if isinstance(a,(UrmInt,UrmFloat)) else 0) * (b.value if isinstance(b,(UrmInt,UrmFloat)) else 0))
        if isinstance(a, UrmString) and isinstance(b, UrmInt): return UrmString(a.value * b.value)
        if isinstance(a, UrmInt) and isinstance(b, UrmString): return UrmString(b.value * a.value)
        raise UrmRuntimeError(f"Cannot multiply {_repr(a)} and {_repr(b)}")
    
    def _div(self, a, b):
        if isinstance(a, UrmInt) and isinstance(b, UrmInt):
            if b.value == 0: raise UrmRuntimeError("Division by zero")
            if a.value % b.value == 0: return UrmInt(a.value // b.value)
            return UrmFloat(a.value / b.value)
        if isinstance(a, (UrmInt,UrmFloat)) or isinstance(b, (UrmInt,UrmFloat)):
            bv = b.value if isinstance(b,(UrmInt,UrmFloat)) else 1
            if bv == 0: raise UrmRuntimeError("Division by zero")
            return UrmFloat((a.value if isinstance(a,(UrmInt,UrmFloat)) else 0) / bv)
        raise UrmRuntimeError(f"Cannot divide {_repr(a)} by {_repr(b)}")
    
    def _floor_div(self, a, b):
        if isinstance(a, UrmInt) and isinstance(b, UrmInt): return UrmInt(a.value // b.value)
        return UrmInt(int((a.value if isinstance(a,(UrmInt,UrmFloat)) else 0) // (b.value if isinstance(b,(UrmInt,UrmFloat)) else 1)))
    
    def _mod(self, a, b):
        if isinstance(a, UrmInt) and isinstance(b, UrmInt): return UrmInt(a.value % b.value)
        return UrmFloat((a.value if isinstance(a,(UrmInt,UrmFloat)) else 0) % (b.value if isinstance(b,(UrmInt,UrmFloat)) else 1))
    
    def _pow(self, a, b):
        if isinstance(a, UrmInt) and isinstance(b, UrmInt): return UrmInt(a.value ** b.value)
        return UrmFloat((a.value if isinstance(a,(UrmInt,UrmFloat)) else 0) ** (b.value if isinstance(b,(UrmInt,UrmFloat)) else 0))
    
    def _compare(self, a, b) -> int:
        if isinstance(a, (UrmInt,UrmFloat)) and isinstance(b, (UrmInt,UrmFloat)):
            av = a.value if isinstance(a,(UrmInt,UrmFloat)) else 0
            bv = b.value if isinstance(b,(UrmInt,UrmFloat)) else 0
            return (av > bv) - (av < bv)
        if isinstance(a, UrmString) and isinstance(b, UrmString):
            return (a.value > b.value) - (a.value < b.value)
        if isinstance(a, UrmBool) and isinstance(b, UrmBool):
            return (a.value > b.value) - (a.value < b.value)
        return 0


# Control flow exceptions
class _ReturnException(Exception):
    def __init__(self, value):
        self.value = value

class _BreakException(Exception):
    def __init__(self, value=None):
        self.value = value or URM_NONE

class _ContinueException(Exception):
    pass
