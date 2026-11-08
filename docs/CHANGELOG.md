# Lord-of-the-Mods
# Changelog

All notable changes to the Lord of the Mods (`lotm`) project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-11-06

### Added
- **Granular Progress Telemetry & Cooperative Cancellation**:
  - Introduced `ProgressReport` structure and `ProgressCallback` (`std::function<bool(const ProgressReport&)>`) across all extraction, packing, and delta patch operations in C++ and Python.
  - Granular telemetry reports `entry_name`, `bytes_transferred`, `file_size`, `total_bytes_transferred`, and `total_archive_size` during multi-megabyte chunk streaming loops.
  - Cooperative preemption: returning `false` (or `Python False`) from `progress_callback` immediately aborts operations with `BigArchiveError` and triggers RAII cleanup.
- **Zero-Copy Buffer Protocol Integration**:
  - `BigPacker.pack_to_memory` and high-level `pack_to_memory` now accept zero-copy Python Buffer Protocol objects (`bytes`, `bytearray`, `memoryview`) via RAII `Py_buffer` pinning.
  - Introduced `BufferAllocator` and `PythonBytesAllocator` to write serialized archive buffers directly into Python `bytes` heap memory without intermediate C++ vector duplication.
- **Single-Asset Chunk Streaming**:
  - Added `stream_entry` to `BigArchive` and `BigOverlay` to stream large asset payloads (e.g. multi-gigabyte video or map files) in 1 MB chunks directly to callbacks without memory spikes.
- **Lookup Performance & Value Semantics**:
  - Optimized `BigArchive` path resolution from $O(N)$ to $O(1)$ via internal lowercase hash indexing.
  - Implemented C++20 value semantics (`operator==`, `operator<=>`) and Python magic methods (`__eq__`, `__lt__`, `__hash__`) for `BigEntry` and `BigOverlayEntry`.
  - Added lifecycle controls (`close()`, `closed`, context manager) to `BigOverlay`.
  - Added `create_directories` strict directory creation flag to `BigArchive::extract_all` and `lotm.big.unpack`.

### Security & Hardening
- **Static CRT & Stable ABI Linkage**:
  - Statically linked MSVC runtime libraries (`/MT`) in Release mode to eliminate external `MSVCP140.dll` dependencies on clean Windows 11 machines.
  - Enabled Python 3.12+ `STABLE_ABI` for forward binary compatibility across Python minor versions.
- **Atomic File Serialization**:
  - Replaced direct in-place output truncation with atomic writes to temporary sibling files (`.lotm_tmp`) followed by `std::filesystem::rename` commits, ensuring pre-existing archives are never corrupted or destroyed on mid-stream exceptions.
- **Header & 32-Bit Limit Hardening**:
  - Enforced strict `total_size >= header_size` validation during archive construction.
  - Upcasted bounds checks to `uintmax_t` to block 32-bit addition wrap-around exploits.

### Changed
- **Command-Line Interface** (Breaking): Removed individual legacy script aliases (`lotm-big-pack`, `lotm-big-unpack`, `lotm-big-diff`, `lotm-big-overlay`) in favor of a centralized subparser architecture. All commands are now invoked through the unified `lotm-big` entry point (`lotm-big pack`, `lotm-big unpack`).
- **CLI Output Isolation**:
  - Isolated CLI command results and summaries to `sys.stdout`, reserving logging handlers strictly for diagnostic telemetry.architecture. All commands are now invoked through the unified `lotm-big` entry point (e.g., `lotm-big pack`, `lotm-big unpack`).

## [0.3.0] - 2026-11-03

### Added
- **Core C++ Engine (`lotm_big`) & Python Bindings**:
  - `BigPacker::pack_to_memory`: Serialize directories or in-memory file buffers (`std::vector<std::pair<std::string, std::vector<uint8_t>>>`) directly into a contiguous BIG4 payload byte array without touching the disk.
  - Glob Filtering: Added `filter_pattern` parameter to `BigArchive::get_entries`, `BigArchive::extract_all`, and `lotm.big.unpack` (supporting `*` and `?` with slash normalization).
  - `BigDiff`: Structural and byte-level comparison engine for `BigArchive` instances categorizing added, removed, modified, and unchanged entries.
  - `BigDiff::create_patch`: Generate minimal, standalone SAGE delta patch `.big` archives directly to disk or memory containing only added and modified entries.
  - `BigOverlay`: SAGE engine load-order emulator computing the effective ("last-wins") virtual file tree across multiple overriding archives.
- **Command-Line Interface**:
  - `lotm-big-unpack`: Added `-f` / `--filter` option for selective glob extraction.
  - `lotm-big-diff`: New command evaluating differences between a base and target archive, with an `-o` / `--output` flag to automatically generate a standalone delta patch archive.
  - `lotm-big-overlay`: New command calculating and visualizing the effective file tree and override history across a specified sequence of `.big` files.

## [0.2.0] - 2026-11-01

### Added
- **Core C++ Engine (`lotm_big`) & Python Bindings**:
  - In-memory single-file extraction via `BigArchive::read_entry()` returning `std::vector<uint8_t>` / Python `bytes` (Buffer Protocol compatible).
  - Python context manager support (`__enter__`, `__exit__`) for `BigArchive` to ensure deterministic lifecycle management and memory cleanup.
  - `closed` property and `close()` method to explicitly release in-memory index structures.

### Security & Hardening
- **NTFS Path Validation**: Hardened extraction against extended Win32 and NT namespace prefixes (`\\?\`, `\\.\`, `\??\`).
- **Drive-Relative Traversal**: Blocked directory traversal attempts using Windows drive-relative paths (e.g., `C:file.txt`).
- **Component Sanitization**: Added strict rejection of NTFS reserved characters (`<`, `>`, `:`, `"`, `|`, `?`, `*`), ASCII control characters, and trailing spaces/dots on individual path components.
- **Golden Master Hex Testing**: Hardened `BigPacker` regression checks with direct raw byte layout verification against authoritative SAGE binary signatures.

### Fixed
- Corrected EA header padding tag to an 8-byte block consisting of `"L219"` followed by 4 null bytes (`\0\0\0\0`), replacing the inaccurate ASCII whitespace padding (`"L219    "`) to match official SAGE archives byte-for-byte.

## [0.1.0] - 2026-10-31

### Added
- **Core C++ Engine (`lotm_big`)**:
  - `BigArchive`: Header parsing, bounds validation, and streaming batch extraction of Electronic Arts BIG4 binary archives.
  - `BigPacker`: Directory tree traversal, SAGE-compliant ASCII sorting, EA `L219` header padding, and atomic archive packing.
  - Little-endian/big-endian conversion routines in `lotm::core` (`endian.hpp`).
- **Python Bindings (`lotm.big`)**:
  - High-level `pack(source_dir, output_file)` and `unpack(archive_path, output_dir)` programmatic APIs with `str` and `os.PathLike` support.
  - Native C++ binding bridge (`_core`) built via `nanobind` and packaged via `scikit-build-core`.
  - Contextual CLI tool (`python -m lotm.big`) supporting `pack`, `unpack`, and `list` operations with progress logging.
- **Test Infrastructure**:
  - Native Catch2 C++ unit test suite targeting endianness, packing invariants, and boundary error conditions.
  - Pytest suite covering GIL release, concurrent multi-threading, and roundtrip data fidelity.
  - OpenCppCoverage integration for MSVC/Ninja on Windows.

### Security & Hardening
- **Zip-Slip & Symlink Defense**: Added pre-flight path normalization and a strict abort policy for any directory symlinks detected along the target extraction path.
- **Zip-Bomb Amplification Limit**: Enforced a `MAX_AMPLIFICATION_RATIO` (20x) quota check across all entry records prior to extraction.
- **Win32 Device Sanitization**: Hardened path validation against reserved DOS device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`) and Alternate Data Streams (`:`), including trailing whitespace/dot evasion.
- **Atomic File Cleanup**: Implemented RAII cleanup guards to automatically remove partially written `.big` archives if serialization is aborted or throws an exception.
- **Case-Insensitive Deduplication**: Added sorting and uniqueness validation in `lotm::big::detail` to prevent game-crashing hash collisions in the SAGE engine.

### Fixed
- Resolved Windows CP_ACP legacy code page crashes by replacing `.string()` conversions with `.u8string()` at the C++/Python boundary.
- Fixed GIL-unlocked reference lifetime leaks by capturing Python callbacks by reference.
- Eliminated root logger pollution by scoping configuration to CLI entry points and adding `logging.NullHandler` to the root package.
