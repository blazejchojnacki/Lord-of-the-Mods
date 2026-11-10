"""
@file _prototype/ini/test_parser.py
@brief PyCharm runner script to parse, reprint, and deeply compare SAGE config files.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from collections import Counter
from dataclasses import dataclass
import difflib
from pathlib import Path
from typing import List, Tuple

try:
    from parser import ConstructFile, IniParseError
except ImportError:
    from _prototype.ini.parser import ConstructFile, IniParseError


@dataclass(frozen=True)
class IndexedLine:
    """Stores a non-empty line alongside its 1-based source line number."""
    line_num: int
    raw: str
    normalized: str
    compact: str


@dataclass(frozen=True)
class CharPos:
    """Maps a non-whitespace character to its 1-based line and column in a file."""
    ch: str
    line_num: int
    col_num: int


def _read_with_fallback(file_path: Path) -> str:
    """Reads text using UTF-8 with a Windows-1252 fallback for legacy SAGE files."""
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return file_path.read_text(encoding="windows-1252")


def _index_non_empty_lines(text: str) -> List[IndexedLine]:
    """Extracts non-empty lines with whitespace-normalized and whitespace-stripped forms."""
    indexed: List[IndexedLine] = []
    for idx, raw_line in enumerate(text.splitlines(), start=1):
        tokens = raw_line.split()
        if not tokens:
            continue
        indexed.append(
            IndexedLine(
                line_num=idx,
                raw=raw_line,
                normalized=" ".join(tokens),
                compact="".join(tokens),
            )
        )
    return indexed


def _build_char_stream(text: str) -> List[CharPos]:
    """Builds a sequence of non-whitespace characters mapped to source line and column."""
    stream: List[CharPos] = []
    for line_idx, line in enumerate(text.splitlines(), start=1):
        for col_idx, ch in enumerate(line, start=1):
            if not ch.isspace():
                stream.append(CharPos(ch=ch, line_num=line_idx, col_num=col_idx))
    return stream


def _find_first_char_mismatch(
    orig_stream: List[CharPos],
    gen_stream: List[CharPos],
    orig_lines: List[str],
    gen_lines: List[str],
) -> str:
    """Finds and formats the exact location of the first non-whitespace character mismatch."""
    min_len = min(len(orig_stream), len(gen_stream))
    mismatch_idx = -1
    for i in range(min_len):
        if orig_stream[i].ch != gen_stream[i].ch:
            mismatch_idx = i
            break

    if mismatch_idx == -1:
        if len(orig_stream) == len(gen_stream):
            return ""
        mismatch_idx = min_len

    lines_out: List[str] = ["--- First Non-Whitespace Character Divergence ---"]
    if mismatch_idx < len(orig_stream):
        o_pos = orig_stream[mismatch_idx]
        o_line = orig_lines[o_pos.line_num - 1].strip()
        o_ctx = "".join(c.ch for c in orig_stream[max(0, mismatch_idx - 15):mismatch_idx + 25])
        lines_out.append(
            f"  Original  [L{o_pos.line_num}:C{o_pos.col_num}] char '{o_pos.ch}' | "
            f"stream: ...{o_ctx}... | line: {o_line}"
        )
    else:
        lines_out.append("  Original  : <EOF reached>")

    if mismatch_idx < len(gen_stream):
        g_pos = gen_stream[mismatch_idx]
        g_line = gen_lines[g_pos.line_num - 1].strip()
        g_ctx = "".join(c.ch for c in gen_stream[max(0, mismatch_idx - 15):mismatch_idx + 25])
        lines_out.append(
            f"  Generated [L{g_pos.line_num}:C{g_pos.col_num}] char '{g_pos.ch}' | "
            f"stream: ...{g_ctx}... | line: {g_line}"
        )
    else:
        lines_out.append("  Generated : <EOF reached>")

    return "\n".join(lines_out)


def analyze_differences(
    original_content: str,
    generated_content: str,
    max_reported_hunks: int = 30,
) -> Tuple[bool, str]:
    """
    Compares original and generated text across three levels:
    1. Continuous non-whitespace character stream (ignores all spaces/newlines).
    2. Unordered multiset of non-empty lines (detects moved lines such as hoisted #defines).
    3. Line-by-line SequenceMatcher diff on whitespace-normalized non-empty lines.
    """
    orig_raw_lines = original_content.splitlines()
    gen_raw_lines = generated_content.splitlines()

    orig_indexed = _index_non_empty_lines(original_content)
    gen_indexed = _index_non_empty_lines(generated_content)

    orig_stream = _build_char_stream(original_content)
    gen_stream = _build_char_stream(generated_content)

    char_stream_equal = (
        len(orig_stream) == len(gen_stream)
        and all(a.ch == b.ch for a, b in zip(orig_stream, gen_stream))
    )

    orig_norm_list = [item.normalized for item in orig_indexed]
    gen_norm_list = [item.normalized for item in gen_indexed]
    norm_lines_equal = orig_norm_list == gen_norm_list

    orig_compact_list = [item.compact for item in orig_indexed]
    gen_compact_list = [item.compact for item in gen_indexed]
    compact_lines_equal = orig_compact_list == gen_compact_list

    report: List[str] = [
        "=" * 72,
        "WHITESPACE-AGNOSTIC COMPARISON REPORT",
        "=" * 72,
        f"Total lines (raw)             : Original = {len(orig_raw_lines):6d} | Generated = {len(gen_raw_lines):6d}",
        f"Non-empty lines               : Original = {len(orig_indexed):6d} | Generated = {len(gen_indexed):6d}",
        f"Non-whitespace characters     : Original = {len(orig_stream):6d} | Generated = {len(gen_stream):6d}",
        f"Continuous char-stream match  : {'YES' if char_stream_equal else 'NO'}",
        f"Per-line compact match        : {'YES' if compact_lines_equal else 'NO'}",
        f"Per-line single-space match   : {'YES' if norm_lines_equal else 'NO'}",
    ]

    if char_stream_equal and norm_lines_equal:
        report.append("=" * 72)
        report.append("SUCCESS: Original and generated files are 100% identical ignoring indentation/blank lines.")
        return True, "\n".join(report)

    if char_stream_equal and not norm_lines_equal:
        report.append(
            "NOTE: Continuous non-whitespace character streams are identical, "
            "meaning differences are strictly intra-line token spacing or line breaks."
        )

    if not char_stream_equal:
        orig_counter = Counter(orig_compact_list)
        gen_counter = Counter(gen_compact_list)
        if orig_counter == gen_counter:
            report.append(
                "NOTE: Both files contain the exact same non-empty lines, "
                "but their order changed (e.g., #define directives hoisted to the top)."
            )
        else:
            missing_counts = orig_counter - gen_counter
            added_counts = gen_counter - orig_counter
            report.append(
                f"Unmatched line multiset delta : "
                f"{sum(missing_counts.values())} original line(s) altered/missing, "
                f"{sum(added_counts.values())} generated line(s) altered/added."
            )

        char_mismatch_info = _find_first_char_mismatch(
            orig_stream, gen_stream, orig_raw_lines, gen_raw_lines
        )
        if char_mismatch_info:
            report.append("")
            report.append(char_mismatch_info)

    matcher = difflib.SequenceMatcher(None, orig_norm_list, gen_norm_list, autojunk=False)
    opcodes = [op for op in matcher.get_opcodes() if op[0] != "equal"]

    if opcodes:
        report.append("")
        report.append(f"--- Normalized Line Diffs (showing up to {max_reported_hunks} of {len(opcodes)} hunks) ---")

        spacing_only_count = 0
        shown_hunks = 0

        for tag, i1, i2, j1, j2 in opcodes:
            if (
                tag == "replace"
                and (i2 - i1) == (j2 - j1)
                and all(
                    orig_indexed[i1 + k].compact == gen_indexed[j1 + k].compact
                    for k in range(i2 - i1)
                )
            ):
                spacing_only_count += (i2 - i1)
                if shown_hunks < max_reported_hunks:
                    shown_hunks += 1
                    for k in range(i2 - i1):
                        o_item = orig_indexed[i1 + k]
                        g_item = gen_indexed[j1 + k]
                        report.append(
                            f"  [SPACING] Orig L{o_item.line_num:<5d}: {o_item.normalized}\n"
                            f"            Gen  L{g_item.line_num:<5d}: {g_item.normalized}"
                        )
                continue

            if shown_hunks >= max_reported_hunks:
                continue
            shown_hunks += 1

            o_range = (
                f"L{orig_indexed[i1].line_num}-L{orig_indexed[i2 - 1].line_num}"
                if i2 > i1
                else f"after L{orig_indexed[i1 - 1].line_num if i1 > 0 else 0}"
            )
            g_range = (
                f"L{gen_indexed[j1].line_num}-L{gen_indexed[j2 - 1].line_num}"
                if j2 > j1
                else f"after L{gen_indexed[j1 - 1].line_num if j1 > 0 else 0}"
            )
            report.append(f"  [{tag.upper()}] Original ({o_range}) vs Generated ({g_range}):")

            for idx in range(i1, min(i2, i1 + 8)):
                o_item = orig_indexed[idx]
                report.append(f"    - [Orig L{o_item.line_num:<5d}] {o_item.normalized}")
            if i2 - i1 > 8:
                report.append(f"    ... ({i2 - i1 - 8} more original lines)")

            for idx in range(j1, min(j2, j1 + 8)):
                g_item = gen_indexed[idx]
                report.append(f"    + [Gen  L{g_item.line_num:<5d}] {g_item.normalized}")
            if j2 - j1 > 8:
                report.append(f"    ... ({j2 - j1 - 8} more generated lines)")

        if spacing_only_count > 0:
            report.append("")
            report.append(
                f"Summary: {spacing_only_count} line(s) differed only in intra-line token spacing "
                f"(e.g., 'key=val' vs 'key = val' or comment spacing)."
            )

    report.append("=" * 72)
    return char_stream_equal, "\n".join(report)


def verify_file_roundtrip(
    input_file: str | Path,
    output_file: str | Path,
    strict: bool = False,
    max_reported_hunks: int = 30,
) -> bool:
    """
    Parses input_file with ConstructFile, writes the reprinted output to output_file,
    and prints a detailed whitespace-agnostic comparison report.
    """
    in_path = Path(input_file)
    out_path = Path(output_file)

    if not in_path.is_file():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    original_content = _read_with_fallback(in_path)

    parsed_construct = ConstructFile(
        name=str(in_path),
        strict=strict,
        file_content=original_content,
    )
    generated_content = parsed_construct.print()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(generated_content, encoding="utf-8")

    print(f"Input file  : {in_path.resolve()}")
    print(f"Output file : {out_path.resolve()}")
    if parsed_construct.errors:
        print(f"Parser warnings/errors ({len(parsed_construct.errors)}):")
        for err in parsed_construct.errors:
            print(f"  ! {err}")

    is_match, report_text = analyze_differences(
        original_content=original_content,
        generated_content=generated_content,
        max_reported_hunks=max_reported_hunks,
    )
    print(report_text)
    return is_match


if __name__ == "__main__":
    # Set the target input file and desired output path here, then run directly in PyCharm
    INPUT_PATH = Path(r"L:\Lord-of-the-Mods_test\copied_aotr_ini\ini\object\neutral\aotrbalroglair.ini")
    OUTPUT_PATH = Path(r"L:/Lord-of-the-Mods/_prototype/ini/file-reformat.ini")

    try:
        verify_file_roundtrip(
            input_file=INPUT_PATH,
            output_file=OUTPUT_PATH,
            strict=False,
            max_reported_hunks=30,
        )
    except IniParseError as e:
        print(f"Parsing failed: {e}")
