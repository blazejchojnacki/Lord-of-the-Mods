# Lord-of-the-Mods
# Changelog

All notable changes to the Lord of the Mods (`lotm`) project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
