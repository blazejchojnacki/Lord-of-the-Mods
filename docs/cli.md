# Lord-of-the-Mods
# Command-Line Interface (CLI)

`lotm` provides terminal commands to inspect, pack, extract, and compare EA BIG4 archives, as well as scan, format, and inspect SAGE `.ini`, `.inc`, and `.str` configuration files.

## 1. Quick Reference

| Command | Action |
|---|---|
| `lotm big pack <source_dir> [-o <out.big>]` | Pack a directory into a BIG4 archive |
| `lotm big unpack <archive> [-o <out_dir>] [-f <pattern>]` | Extract an archive into a target directory |
| `lotm big diff <base.big> <target.big> [-o <patch.big>]` | Compare two archives and generate a delta patch |
| `lotm big overlay <archive1> <archive2> ...` | Emulate SAGE load-order and preview virtual file tree |
| `lotm ini scan <target> [-o <report>] [--strict]` | Scan `.ini`, `.inc`, and `.str` files for structural errors |
| `lotm ini format <file> [-o <out>] [--strict]` | Format a configuration file with normalized 4-space indentation |
| `lotm ini inspect <file> [--strict]` | Display AST block breakdown, macro counts, and diagnostics |
| `python -m lotm ...` | Fallback umbrella module execution |
| `lotm-big ...` | Domain alias shortcut for BIG operations |

---

## 2. Packing Archives (`lotm big pack`)

Compresses a folder structure into a `.big` archive, automatically normalizing path separators, sorting the index table alphabetically for SAGE binary search compatibility, and applying EA `L219` header padding.

```cmd
lotm big pack "mod_workspace/data" -o "my_mod.big"
```

**Options:**
* `source_dir`: Directory containing source files (Positional, Required).
* `-o`, `--output`: Destination archive path (Default: `./packed_archive.big`).
* `-v`, `--verbose`: Enable detailed file-by-file packing telemetry on stdout.

---

## 3. Unpacking Archives (`lotm big unpack`)

Extracts entries from a BIG4 container while enforcing path sanitization, amplification ratio quotas, and Win32 device checks.

```cmd
lotm big unpack "my_mod.big" -o "workspace_dump" -f "data/ini/*.ini"
```

**Options:**
* `archive`: Path to the source `.big` file (Positional, Required).
* `-o`, `--output`: Target extraction directory (Default: `./extracted_files`).
* `-f`, `--filter`: Optional glob pattern (`*`, `?`) to selectively extract matching files.
* `-v`, `--verbose`: Enable detailed extraction telemetry on stdout.

---

## 4. Archive Comparison & Delta Patching (`lotm big diff`)

Compares a base archive against a modified archive and prints a primary summary to stdout detailing added, removed, and modified files. Can automatically pack these differences into a minimal delta patch archive.

```cmd
lotm big diff "vanilla.big" "modded.big" -o "release_patch.big"
```

**Options:**
* `base_archive`: Path to the baseline `.big` file (Positional, Required).
* `target_archive`: Path to the modified `.big` file (Positional, Required).
* `-o`, `--output`: Optional destination path to generate a delta patch `.big` containing only modified and added files.
* `-f`, `--filter`: Optional glob pattern to restrict the scope of the comparison.
* `-v`, `--verbose`: Output the exact names and sizes of individual changed files directly to stdout.

---

## 5. Load-Order Emulation (`lotm big overlay`)

Simulates the SAGE engine's alphabetical or explicit archive load-order priority, resolving the "last-wins" effective virtual file tree, and printing the results to stdout.

```cmd
lotm big overlay "03_mod.big" "01_patch.big" -f "*.dds"
```

**Options:**
* `sources`: A directory path (to mount all `.big` files alphabetically) or a sequence of explicit `.big` file paths evaluated in the given order.
* `-f`, `--filter`: Optional glob pattern to inspect specific resolved files.
* `-v`, `--verbose`: Output the override history and winning source archive for each resolved file directly to stdout.

---

## 6. Scanning Configuration Files (`lotm ini scan`)

Scans a single `.ini`, `.inc`, or `.str` file—or recursively scans an entire directory tree—for delimiter mismatches, negative nesting levels, unclosed blocks at EOF, and orphaned `.str` statements.

```cmd
lotm ini scan "mod_workspace/data/ini" -o "scan_report.txt" --strict
```

**Options:**
* `target`: Path to a `.ini`, `.inc`, or `.str` file, or a directory to scan recursively (Positional, Required).
* `-o`, `--output`: Optional destination file path to save the diagnostic scan report.
* `--strict`: Exit with a non-zero error code (`1`) if any structural or delimiter errors are detected.

---

## 7. Formatting Configuration Files (`lotm ini format`)

Parses a SAGE `.ini`, `.inc`, or `.str` file into its AST representation and serializes it back with normalized 4-space block indentation while preserving all inline comments, standalone comments, `#define` macros, and `#include` directives.

```cmd
lotm ini format "mod_workspace/data/ini/weapon.ini" -o "weapon_formatted.ini" --strict
```

**Options:**
* `file`: Path to the source `.ini`, `.inc`, or `.str` file (Positional, Required).
* `-o`, `--output`: Destination file path (Default: overwrites `file` in-place).
* `--strict`: Abort formatting and exit with a non-zero status code if any structural errors exist in the input file.

---

## 8. Inspecting Configuration Files (`lotm ini inspect`)

Parses a configuration or localization file and prints a structural summary report detailing the recognized starting nesting level, `#define` count, `#include` count, top-level block frequency breakdown, and any non-strict warnings.

```cmd
lotm ini inspect "mod_workspace/data/ini/object/gondor/aragorn.ini"
```

**Options:**
* `file`: Path to the `.ini`, `.inc`, or `.str` file to inspect (Positional, Required).
* `--strict`: Fail with a non-zero status code if the file contains structural errors.
