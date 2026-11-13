# SAGE Engine INI Parser: Feature Summary & C++ Translation Specs

This document outlines the architectural features of the Lord of the Mods (lotm) SAGE Engine INI parser, validated through the Python prototype, and serves as the specification blueprint for the native C++20 implementation.

## 1. Core Parser Features
* **Lossless Roundtrip Fidelity:** The parser guarantees 100% syntactical reconstruction of `.ini`, `.inc`, and `.str` files. Inline comments, standalone comments, key-value pairs, and block headers are perfectly preserved during serialization.
* **Schema-Driven Delimiters:** Block starts are identified using hardcoded schema tables rather than regex or dynamic string matching, mapping exactly to specific object hierarchies.
* **Iterative Serializer:** AST stringification (`.print()`) is executed via a flat, iterative stack loop rather than recursive method calls, preventing stack overflow (RecursionError/StackOverflow) on deeply nested files.

## 2. Handled SAGE Engine Quirks & Edge Cases
* **Opaque Script Blocks (`BeginScript`):** Intercepted natively to generate a `ScriptNode`. Inner lines are consumed as raw text until `EndScript` is found, protecting the parser from colliding with Lua-style `end` keywords (e.g., in `watertextures.ini`).
* **Dynamic `FCurve` Interception:** Lines matching `<key> = FCurve` are dynamically promoted into `ConstructLevel` blocks (with `_class="<key> ="`), avoiding wildcards in the core delimiter tables.
* **Transparent Wrappers:** Tags like `ReplaceModule` shift the schema lookup depth by 1, allowing their inner contents to correctly map to standard inner-block schemas.
* **Closure Token Tolerance:** Safely maps `End`, `END`, and `end` to structural closure rules.
* **Lossless `#include` Directives:** Preprocessor includes are retained as discrete `IncludeNode`s, capturing the raw string without eager expansion. This supports GUI preview sandboxing, lossless saving, and dynamic refactoring when referenced files move.

## 3. Security & Stability Mechanics
* **Hardcoded Depth Guard (`MAX_INI_DEPTH = 16`):** The parser strictly enforces a maximum nesting limit. Pushing past this depth triggers an immediate `IniParseError`, shielding against malicious Zip-bomb/stack-exhaustion payloads.
* **Virtual Chroot Sandboxing:** Includes an on-demand `validate_include` routine that computes absolute canonical paths and strictly enforces containment within a designated virtual root (e.g., `data/ini`), preventing Local File Inclusion (LFI) via path traversal (`../`).
* **EOF Integrity Checking:** An optional strict mode (`strict=True`) validates that the final parser depth matches the starting depth, explicitly raising an error for unclosed blocks, while standard mode securely logs the warnings.

---

## 4. C++20 Translation Requirements

To achieve industry-grade performance and safety, the C++20 port must adhere to the following constraints:

### A. Zero-Copy Lexing & Parsing
* Python's `.replace('=', ' = ').split()` string allocations must be discarded.
* The C++ lexer must operate over a single contiguous memory buffer (via `std::vector<char>` or OS-level memory mapping).
* Tokenization must emit `std::string_view` slices pointing directly into the source buffer, strictly avoiding `std::string` heap allocations during the parsing loop.

### B. Compile-Time Schema Tables
* `INI_DELIMITERS` and `STR_DELIMITERS` must be translated into `constexpr std::array` structures of `std::span<const std::string_view>` to guarantee zero runtime initialization overhead and immediate lookups.

### C. Polymorphic AST via `std::variant`
* Nodes must be modeled as a variant type: `using AstNode = std::variant<CommentNode, StatementNode, IncludeNode, ScriptNode, ConstructLevel>;`
* Standard iterative traversal and serialization must utilize `std::visit` and `std::vector<SerializationFrame>` rather than recursive virtual function calls.
* Consider arena allocation for `ConstructLevel` child vectors if cache locality bottlenecks arise during bulk corpus scans.

### D. Engine Bound Safety
* Legacy SAGE engine string buffers are finite. While the parser reads arbitrary lengths, the C++ AST Builder API must enforce length validations on `name` and `identifier` fields to prevent downstream buffer overflows in the 32-bit game executable.

### E. Python Bindings (`nanobind`)
* The C++ parser must be exposed to Python using `nanobind`.
* Operations processing entire files or serializing large ASTs must wrap execution in `nb::gil_scoped_release` to ensure thread concurrency when batch-processing thousands of mod files.
