# Lord-of-the-Mods
# SAGE Engine INI Parser & AST Architecture

The Lord of the Mods (`lotm.ini`) configuration engine provides a high-performance, structurally aware parser for SAGE engine `.ini`, `.inc`, and `.str` files. 

Because the SAGE engine utilizes a highly custom configuration format that standard INI parsers (like Python's `configparser`) cannot understand, `lotm` implements a bespoke Abstract Syntax Tree (AST) engine in C++20. This engine is designed to be completely lossless, highly secure, and seamlessly accessible from Python.

## 1. Core Capabilities

*   **100% Lossless Roundtrip Fidelity:** The parser guarantees exact syntactical reconstruction of `.ini`, `.inc`, and `.str` files. Inline comments, standalone comments, `#define` macros, `#include` directives, key-value pairs, and exact block headers are perfectly preserved during serialization. If you parse a file and immediately print it, the output will match the original character-for-character.
*   **Compile-Time Schema Delimiters:** Block starts are identified using compile-time `constexpr` lookup tables sorted by descending token count. This maps block headers exactly to known SAGE object hierarchies without the heavy performance overhead of regular expressions.
*   **Iterative Serializer:** Serializing an AST back into text (`.print()`) is executed via a flat, non-recursive stack loop. This prevents stack overflow crashes (`RecursionError`) on deeply nested files.

## 2. The Abstract Syntax Tree (AST)

When a file is parsed, it is converted into an object-oriented AST. You can interact with these nodes directly in Python to analyze or safely mutate mod data.

### Standard Configuration (`.ini`, `.inc`)
*   **`ConstructFile`**: The root document container. It holds top-level `#define` macros, `#include` directives, and the file's primary AST blocks (`items`).
*   **`ConstructLevel`**: Represents a nested block (e.g., `Object`, `Weapon`, `Armor`). It contains a `_class`, `name`, `identifier`, and a list of inner `items`.
*   **`ScriptNode`**: An opaque container specifically for `BeginScript ... EndScript` blocks. It preserves raw Lua code lines (`content`) safely.
*   **`IncludeNode`**: Represents a `#include` directive, preserving the raw path string while providing a normalized `.clean_path` property for resolution.
*   **`StatementNode`**: A standard key-value assignment or property line (e.g., `Damage = 100`).
*   **`CommentNode`**: A standalone comment line.

### Localization Dictionaries (`.str`)
*   **`StrDocument`**: The root document for a localization file, containing `entries` and capturing any non-strict parsing warnings.
*   **`StrEntry`**: A single localized string block. It contains a `category` (e.g., `OBJECT`, `GUI`), an `identifier`, and a list of inner string statements and comments.

## 3. Handling SAGE Engine Quirks

The parser natively handles the eccentricities of the SAGE engine format:

*   **Quote-Aware & URL-Aware Comments:** The lexer tracks double-quoted string literals (`"..."`). Semicolons (`;`) and double slashes (`//`) inside localized strings are safely ignored. Furthermore, it ignores `//` immediately preceded by a colon, ensuring unquoted URLs (like `http://` in `WebpageURL` blocks) are never accidentally truncated as comments.
*   **Opaque Lua Scripts:** `BeginScript` blocks are intercepted natively. Inner lines are consumed as raw text until `EndScript` is encountered, completely eliminating collisions with Lua's own `end` keywords (a common issue in files like `watertextures.ini`).
*   **Dynamic `FCurve` Interception:** Lines matching `<key> = FCurve` are dynamically promoted into proper `ConstructLevel` blocks, avoiding wildcard hacks in the core delimiter tables.
*   **Transparent Wrappers:** Tags like `ReplaceModule` shift the internal schema lookup depth by 1, allowing their inner contents (like `Body = ActiveBody`) to map cleanly to standard inner-block schemas.
*   **Multi-Flag Block Headers:** Block headers with two or more trailing tokens (such as `AnimationState = MOVING SPECIAL_ONE DAMAGED`) are handled gracefully: the first token becomes the `name`, and the remaining tokens are joined into the `identifier`.
*   **Closure Token Tolerance:** Safely maps `End`, `END`, and `end` to structural closure rules case-insensitively.

## 4. Security & Safety Constraints

To protect tools and end-users from malicious mod files (e.g., Zip-bombs, path traversal attacks, or memory exhaustion), the parser enforces strict hardware and engine boundaries:

*   **Nesting Depth Guard (`MAX_INI_DEPTH = 16`):** Strictly enforces a maximum nesting limit across standard blocks, `FCurve` blocks, and `BeginScript` transitions. Exceeding this depth throws an `IniParseError` to block stack-exhaustion attacks.
*   **Maximum File Size Guard (`MAX_INI_FILE_SIZE = 64 MiB`):** Prevents Out-Of-Memory (OOM) denial-of-service payloads when reading oversized files or memory buffers.
*   **Virtual Chroot Sandboxing (`validate_include`):** Canonicalizes UTF-8 paths relative to the current file's directory or the virtual root (e.g., `data/ini`). It verifies containment within the virtual root, actively blocking Local File Inclusion (LFI) via path traversal (`../`).
*   **Legacy 32-Bit Engine Buffer Limits:** Enforces `SAGE_MAX_BLOCK_NAME_LEN` (256 bytes) on block classes/names and `SAGE_MAX_IDENTIFIER_LEN` (512 bytes) on identifiers. This is enforced across C++ constructors, parser transitions, and Python property setters to prevent buffer overflows in the 32-bit SAGE executable.
*   **EOF Integrity Checking:** In `strict=True` mode, the parser validates that the final depth matches the starting depth and that all `.str` entries are properly closed, raising an exception on mismatches. Lenient mode (`strict=False`) records these as diagnostics instead.

## 5. Performance & Python Bindings

*   **Zero-Copy Lexing & Encoding Fallbacks:** Files are memory-mapped into read-only pages via Win32 `CreateFileMappingW` using strict UTF-8 path conversions. The parser slices lines into `std::string_view` tokens directly over the contiguous buffer. It strips UTF-8 BOMs and validates UTF-8 in a single zero-allocation pass, transcoding to UTF-8 only when legacy Windows-1252 / Latin-1 bytes are detected.
*   **Buffer Protocol Integration:** The Python API can parse `bytes`, `bytearray`, or `memoryview` objects zero-copy. This allows payloads retrieved directly from a `.big` archive to be parsed into an AST without intermediate string decoding or disk writes.
*   **In-Place AST Mutation (`nanobind` Reference Semantics):** Container indexing (`node[i]`) and iteration (`for child in node:`) on AST structures return internal references (`nb::rv_policy::reference_internal`). This means modifying a node's property in Python mutates the underlying C++ object directly, ensuring changes are perfectly reflected when you call `.print()` or `format_ini`.
