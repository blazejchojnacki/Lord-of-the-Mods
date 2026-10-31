# Lord-of-the-Mods
# Command-Line Interface (CLI)

`lotm` provides terminal commands to inspect, pack, and extract EA BIG4 archives.

## 1. Quick Reference

| Command | Action |
|---|---|
| `lotm-big-pack <source_dir> [-o <out.big>]` | Pack a directory into a BIG4 archive |
| `lotm-big-unpack <archive> [-o <out_dir>]` | Extract an archive into a target directory |
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

---

## 3. Unpacking Archives (`lotm-big-unpack`)

Extracts all entries from a BIG4 container while enforcing path sanitization, amplification ratio quotas, and Win32 device checks.

```cmd
lotm-big-unpack "my_mod.big" -o "workspace_dump"
```

**Options:**
* `archive`: Path to the source `.big` file (Positional, Required).
* `-o`, `--output`: Target extraction directory (Default: `./extracted_files`).
* 