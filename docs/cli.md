# Lord-of-the-Mods
# Command-Line Interface (CLI)

The `lotm` repository includes standalone shell scripts to manipulate BIG4 archives directly from the terminal.

## Packing Archives (`big_pack.py`)

Compresses a standard file directory into a `.big` archive, automatically aligning headers and sorting the internal index alphabetically for SAGE bsearch compatibility.

**Usage:**
```cmd
python -m lotm/big/big_pack <source_dir> [-o <output_file>]
```
**Arguments:**

`source_dir`: Path to the directory containing your mod files. (Required)

`-o`, `--output`: Destination `.big` file path. (Default: `./packed_archive.big`)

Example:
```cmd 
python -m lotm/big/big_pack "mod_workspace/data" -o "my_mod.big"
```

## Unpacking Archives (big_unpack.py)
Extracts all files from a BIG4 archive into a standard directory tree.

**Usage:**
```cmd
python -m lotm/big/big_unpack <archive> [-o <output_dir>]
```
**Arguments:**

`archive`: Path to the source `.big` file. (Required)

`-o`, `--output`: Destination directory. (Default: `./extracted_files`)

**Example:**
```cmd
python -m lotm/big/big_unpack "my_mod.big" -o "workspace_dump"
```
