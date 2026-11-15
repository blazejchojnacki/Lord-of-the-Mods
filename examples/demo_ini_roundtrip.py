"""
@file examples/demo_ini_roundtrip.py
@brief PyCharm demo script for lotm.ini AST deconstruction, formatting, and diff logging.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import difflib
import sys
from pathlib import Path

import lotm.ini as ini


def setup_dummy_file(path: Path) -> str:
    """
    Create a slightly malformed SAGE INI file to demonstrate formatting corrections.

    Parameters
    ----------
    path : Path
        Destination file path where the unformatted sample INI payload will be written.

    Returns
    -------
    str
        Raw unformatted configuration text written to `path`.

    Examples
    --------
    >>> text = setup_dummy_file(Path("demo_workspace/original.ini"))  # doctest: +SKIP
    """
    messy_content = (
        "; Messy SAGE Configuration\n"
        "Object GondorFighter\n"
        "ArmorSet\n"
        "Conditions = NONE\n"
        "Armor =   SoldierArmor\n"
        "End\n"
        "Draw =W3DScriptedModelDraw ModuleTag_01\n"
        "DefaultModelConditionState\n"
        "Model=GUSoldier_SKN\n"
        "End\n"
        "AnimationState= MOVING\n"
        "BeginScript\n"
        "CurDrawableSetTransitionAnimState(\"TRANS_Move\")\n"
        "EndScript\n"
        "End\n"
        "End\n"
        "End\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(messy_content, encoding="utf-8")
    return messy_content


def main() -> int:
    """
    Execute the INI AST deconstruction, re-serialization, and unified diff demonstration.

    Returns
    -------
    int
        Process exit code (0 on success, 1 on fatal parse error).

    Examples
    --------
    >>> exit_code = main()  # doctest: +SKIP
    """
    workspace = Path(__file__).parent.resolve() / "demo_workspace"
    original_path = workspace / "original.ini"
    formatted_path = workspace / "formatted.ini"

    print(f"--- lotm.ini Roundtrip Demo ---")

    # 1. Prepare
    original_text = setup_dummy_file(original_path)
    print(f"Created messy input file: {original_path.relative_to(workspace.parent)}")

    # 2. Deconstruct (Parse to AST)
    print("Parsing AST...")
    try:
        ast_doc = ini.parse_ini(original_path, strict=True)
    except ini.IniParseError as e:
        print(f"Fatal parsing error: {e}", file=sys.stderr)
        return 1

    print(f"Successfully deconstructed {len(ast_doc)} top-level item(s).")

    # 3. Serialize and Save
    print(f"Serializing AST to {formatted_path.relative_to(workspace.parent)}...")
    formatted_text = ast_doc.print()
    formatted_path.write_text(formatted_text, encoding="utf-8")

    # 4. Compare and Log Changes
    print("\n--- Change Log (Unified Diff) ---")

    original_lines = original_text.splitlines(keepends=True)
    formatted_lines = formatted_text.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        original_lines,
        formatted_lines,
        fromfile="Original (Messy)",
        tofile="Formatted (lotm AST)",
        n=1  # Number of context lines to show around changes
    ))

    if not diff:
        print("No changes detected. The file was already perfectly formatted.")
    else:
        for line in diff:
            # Colorize output slightly for PyCharm console readability
            clean_line = line.rstrip('\n')
            if clean_line.startswith('+') and not clean_line.startswith('+++'):
                print(f"\033[92m{clean_line}\033[0m")  # Green for additions
            elif clean_line.startswith('-') and not clean_line.startswith('---'):
                print(f"\033[91m{clean_line}\033[0m")  # Red for removals
            elif clean_line.startswith('@'):
                print(f"\033[96m{clean_line}\033[0m")  # Cyan for chunks
            else:
                print(clean_line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
