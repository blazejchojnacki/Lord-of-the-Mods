# Lord-of-the-Mods
# Command-Line Interface (CLI)

`lotm` provides terminal commands to inspect, pack, extract, and compare EA BIG4 archives.

## 1. Quick Reference

| Command | Action |
|---|---|
| `lotm-big-pack <source_dir> [-o <out.big>]` | Pack a directory into a BIG4 archive |
| `lotm-big-unpack <archive> [-o <out_dir>] [-f <pattern>]` | Extract an archive into a target directory |
| `lotm-big-diff <base.big> <target.big> [-o <patch.big>]` | Compare two archives and generate a delta patch |
| `lotm-big-overlay <archive1> <archive2> ...` | Emulate SAGE load-order and preview virtual file tree |
| `python -m lotm.big pack ...` | Fallback module execution |
| `python -m lotm.big unpack ...` | Fallback module execution |

---

## 2. Packing Archives (`lotm-big-pack`)

Compresses a folder structure into a `.big` archive, automatically normalizing path separators, sorting the index table alphabetically for SAGE binary search compatibility, and applying EA `L219` header padding.

```cmd
lotm-big-pack "mod_workspace/data" -o "my_mod.big"
```

**Options:**
* `source_dir`: Directory containing source files (Positional, Required).
* `-o`, `--output`: Destination archive path (Default: `./packed_archive.big`).
* `-v`, `--verbose`: Enable detailed file packing logs.

---

## 3. Unpacking Archives (`lotm-big-unpack`)

Extracts entries from a BIG4 container while enforcing path sanitization, amplification ratio quotas, and Win32 device checks.

```cmd
lotm-big-unpack "my_mod.big" -o "workspace_dump" -f "data/ini/*.ini"
```

**Options:**
* `archive`: Path to the source `.big` file (Positional, Required).
* `-o`, `--output`: Target extraction directory (Default: `./extracted_files`).
* `-f`, `--filter`: Optional glob pattern (`*`, `?`) to selectively extract matching files.
* `-v`, `--verbose`: Enable detailed extraction logs.

---

## 4. Archive Comparison & Delta Patching (`lotm-big-diff`)

Compares a base archive against a modified archive and outputs a summary of added, removed, and modified files. Can automatically pack these differences into a minimal delta patch archive.

```cmd
lotm-big-diff "vanilla.big" "modded.big" -o "release_patch.big"
```

**Options:**
* `base_archive`: Path to the baseline `.big` file (Positional, Required).
* `target_archive`: Path to the modified `.big` file (Positional, Required).
* `-o`, `--output`: Optional destination path to generate a delta patch `.big` containing only modified and added files.
* `-f`, `--filter`: Optional glob pattern to restrict the scope of the comparison.
* `-v`, `--verbose`: Log individual file changes to the console.

---

## 5. Load-Order Emulation (`lotm-big-overlay`)

Simulates the SAGE engine's alphabetical or explicit archive load-order priority, resolving the "last-wins" effective virtual file tree.

```cmd
lotm-big-overlay "03_mod.big" "01_patch.big" -f "*.dds"
```

**Options:**
* `sources`: A directory path (to mount all `.big` files alphabetically) or a sequence of explicit `.big` file paths evaluated in the given order.
* `-f`, `--filter`: Optional glob pattern to inspect specific resolved files.
* `-v`, `--verbose`: Output the override history and winning source archive for each resolved file.
