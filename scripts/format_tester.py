"""
@file format_tester.py
@brief Script to format and structurally compare a SAGE configuration file.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

import sys
from pathlib import Path
from lotm.ini import parse_ini_file, parse_str_file, unwrap_node, CommentNode


def normalize_text(text: str) -> str:
    """Normalize text by stripping whitespace and removing leading comment tokens."""
    text = text.strip()
    if text.startswith(";"):
        text = text[1:].strip()
    elif text.startswith("//"):
        text = text[2:].strip()
    return text


def extract_meaningful_content(file_path: Path) -> list[str]:
    """Extract and normalize non-empty lines from a file."""
    lines = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            norm = normalize_text(line)
            if norm:
                lines.append(norm)
    return lines


def format_and_compare(target_path: Path) -> None:
    """Parse a file, format it to a new file, and compare their structural content."""
    print(f"Target File: {target_path.resolve()}")
    if not target_path.exists() or not target_path.is_file():
        print("Error: Target path does not exist or is not a file.")
        return

    ext = target_path.suffix.lower()
    if ext not in {".ini", ".inc", ".str"}:
        print(f"Error: Unsupported file extension '{ext}'. Supported: .ini, .inc, .str")
        return

    # 1. Parse into AST
    print("\n[1/3] Parsing file into AST...")
    if ext == ".str":
        ast = parse_str_file(target_path, strict=False)
    else:
        ast = parse_ini_file(target_path, strict=False)

    if ast.errors:
        print("Warnings during parsing:")
        for err in ast.errors:
            print(f"  - {err}")

    # 2. Format to a new file
    print("\n[2/3] Generating formatted output...")
    formatted_content = ast.print()

    output_path = target_path.with_name(f"{target_path.stem}_formatted{target_path.suffix}")
    output_path.write_text(formatted_content, encoding="utf-8")
    print(f"Saved formatted file to: {output_path.resolve()}")

    # 3. Compare meaningful content
    print("\n[3/3] Comparing structural content...")
    original_lines = extract_meaningful_content(target_path)
    formatted_lines = extract_meaningful_content(output_path)

    if original_lines == formatted_lines:
        print("\n✅ SUCCESS: Formatted content matches the original structurally.")
    else:
        print("\n❌ MISMATCH: Structural differences detected.")
        print(f"  Original meaningful lines: {len(original_lines)}")
        print(f"  Formatted meaningful lines: {len(formatted_lines)}")

        # Basic diff of the first mismatch
        for i in range(min(len(original_lines), len(formatted_lines))):
            if original_lines[i] != formatted_lines[i]:
                print(f"\nFirst mismatch at structural index {i}:")
                print(f"  Original : '{original_lines[i]}'")
                print(f"  Formatted: '{formatted_lines[i]}'")
                break
        else:
            if len(original_lines) != len(formatted_lines):
                print("\nMismatch at the end of the file.")


if __name__ == "__main__":
    # To run in PyCharm: 
    # 1. Open this file.
    # 2. Change 'TARGET_FILE_PATH' below to point to the file you want to test.
    # 3. Right-click anywhere in this editor and select "Run 'format_tester'".

    # ---------------------------------------------------------
    # EDIT THIS PATH:
    TARGET_FILE_PATH = r"L:\Lord-of-the-Mods_test\copied_aotr_ini\ini\object\commandpointgenerator.ini"
    # TARGET_FILE_PATH = r"L:\Lord-of-the-Mods_test\copied_aotr_ini\ini\object\fortressringfunc.inc"
    # TARGET_FILE_PATH = r
    # ---------------------------------------------------------

    target = Path(TARGET_FILE_PATH)
    format_and_compare(target)
