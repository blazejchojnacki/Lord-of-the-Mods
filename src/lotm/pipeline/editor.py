"""
@file src/lotm/pipeline/editor.py
@brief Zero-copy archive-to-AST session editor and standalone transformation helpers.

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from collections.abc import Buffer, Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass, field
import fnmatch
import logging
import os
from pathlib import Path
import tempfile
from typing import TypeAlias

from lotm._core import big as _big
from lotm.big import pack_to_memory
from lotm.ini import ConstructFile, FormatOptions, StrDocument, parse_ini, parse_str

from .stages import EntryStage

logger = logging.getLogger("lotm.pipeline.editor")

ArchiveHandle: TypeAlias = _big.BigArchive | _big.BigOverlay
ArchiveInput: TypeAlias = str | os.PathLike[str] | ArchiveHandle


@dataclass
class TransformResult:
    """
    Summary of staged entry changes and serialized archive output.

    Attributes
    ----------
    modified_entries : list[str]
        Normalized/canonical entry names modified from the source archive or overlay.
    added_entries : list[str]
        Entry names newly added and not present in the source archive or overlay.
    removed_entries : list[str]
        Entry names removed from the source archive or overlay.
    output_bytes : bytes | None
        Serialized `.big` archive bytes when generated in memory, else `None`.
    output_path : Path | None
        Destination `.big` file path when written to disk, else `None`.
    """

    modified_entries: list[str] = field(default_factory=list)
    added_entries: list[str] = field(default_factory=list)
    removed_entries: list[str] = field(default_factory=list)
    output_bytes: bytes | None = None
    output_path: Path | None = None


def _normalize_archive_path(entry_name: str) -> str:
    """Normalize virtual archive path separators to backslashes."""
    return entry_name.replace("/", "\\")


def _normalize_key(entry_name: str) -> str:
    """Normalize a virtual archive entry path for case-insensitive lookups."""
    return entry_name.replace("\\", "/").lower()


def _matches_glob(entry_name: str, pattern: str | None) -> bool:
    """Match an entry path case-insensitively against a glob pattern."""
    if not pattern or pattern == "*":
        return True
    return fnmatch.fnmatchcase(_normalize_key(entry_name), _normalize_key(pattern))


def _write_atomic_bytes(output_file: str | os.PathLike[str], data: bytes) -> Path:
    """Write `data` atomically to `output_file` via a sibling temporary file."""
    dest = Path(output_file)
    if dest.exists() and dest.is_dir():
        raise ValueError(f"Target output path cannot be a directory: {dest}")
    if not dest.parent.is_dir():
        raise FileNotFoundError(f"Target output directory '{dest.parent}' does not exist.")

    fd, tmp_name = tempfile.mkstemp(prefix=f".{dest.name}.", suffix=".lotm_tmp", dir=str(dest.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, dest)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    return dest


class ArchiveEditor:
    """
    Zero-copy archive session bridging `lotm.big` payloads and `lotm.ini` ASTs.

    Supports opening from a `.big` file path (managed automatically via context
    manager or `close()`) or borrowing an existing open `BigArchive` or `BigOverlay`.

    Parameters
    ----------
    source : str | os.PathLike[str] | BigArchive | BigOverlay
        Source `.big` archive path, open `BigArchive`, or open `BigOverlay`.

    Examples
    --------
    >>> from lotm.big import pack_to_memory
    >>> raw = pack_to_memory({"data/weapon.ini": b"Weapon Sword\\n    Damage = 10\\nEnd\\n"})
    >>> with ArchiveEditor(raw) if False else ...:  # doctest: +SKIP
    ...     pass
    """

    def __init__(self, source: ArchiveInput) -> None:
        self._stack = ExitStack()
        self._closed = False
        self._source_handle: ArchiveHandle
        self._base_entries_by_key: dict[str, tuple[str, int]] = {}
        self._ini_asts: dict[str, tuple[str, ConstructFile, FormatOptions | None]] = {}
        self._str_asts: dict[str, tuple[str, StrDocument, FormatOptions | None]] = {}
        self._raw_overrides: dict[str, tuple[str, bytes]] = {}
        self._removed_keys: set[str] = set()

        if isinstance(source, (_big.BigArchive, _big.BigOverlay)):
            if source.closed:
                raise _big.BigArchiveError("Cannot open ArchiveEditor on a closed archive or overlay.")
            self._source_handle = source
        else:
            arc_path = Path(source)
            if not arc_path.is_file():
                raise FileNotFoundError(f"Archive not found: {arc_path}")
            opened = self._stack.enter_context(_big.BigArchive(arc_path))
            self._source_handle = opened

        for entry in self._source_handle.get_entries():
            key = _normalize_key(entry.name)
            self._base_entries_by_key[key] = (entry.name, int(entry.size))

    @property
    def closed(self) -> bool:
        """Return True if this editor session has been closed."""
        return self._closed

    def close(self) -> None:
        """Release any owned resources and mark the editor as closed."""
        if not self._closed:
            self._closed = True
            self._stack.close()

    def __enter__(self) -> ArchiveEditor:
        """Enter the context manager and return `self`."""
        if self._closed:
            raise _big.BigArchiveError("Cannot enter context with a closed ArchiveEditor.")
        return self

    def __exit__(self, exc_type: object = None, exc_val: object = None, exc_tb: object = None) -> None:
        """Exit the context manager and close owned resources."""
        self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            raise _big.BigArchiveError("Cannot operate on a closed ArchiveEditor.")
        if self._source_handle.closed:
            raise _big.BigArchiveError("Underlying archive or overlay has been closed.")

    def _read_source_bytes(self, entry_name: str) -> tuple[str, bytes]:
        """Resolve and read zero-copy `bytes` from the underlying archive or overlay."""
        self._ensure_open()
        resolved = self._source_handle.resolve(entry_name)
        canonical_name = _normalize_archive_path(resolved.name)
        payload = self._source_handle.read_entry(resolved.name)
        return canonical_name, payload

    def open_ini(self, entry_name: str, *, strict: bool = False) -> ConstructFile:
        """
        Parse a `.ini` or `.inc` archive entry zero-copy into a cached `ConstructFile` AST.

        Subsequent calls for the same case-insensitive entry path return the same
        mutable `ConstructFile` instance until committed.
        """
        self._ensure_open()
        key = _normalize_key(entry_name)
        if key in self._ini_asts:
            return self._ini_asts[key][1]

        if key in self._raw_overrides:
            canon_name, raw_buf = self._raw_overrides[key]
            doc = parse_ini(canon_name, strict=strict, file_content=raw_buf)
        else:
            canon_name, raw_buf = self._read_source_bytes(entry_name)
            doc = parse_ini(canon_name, strict=strict, file_content=raw_buf)

        self._ini_asts[key] = (canon_name, doc, None)
        self._removed_keys.discard(key)
        return doc

    def open_str(self, entry_name: str, *, strict: bool = False) -> StrDocument:
        """
        Parse a `.str` localization archive entry zero-copy into a cached `StrDocument` AST.

        Subsequent calls for the same case-insensitive entry path return the same
        mutable `StrDocument` instance until committed.
        """
        self._ensure_open()
        key = _normalize_key(entry_name)
        if key in self._str_asts:
            return self._str_asts[key][1]

        if key in self._raw_overrides:
            canon_name, raw_buf = self._raw_overrides[key]
            doc = parse_str(canon_name, strict=strict, file_content=raw_buf)
        else:
            canon_name, raw_buf = self._read_source_bytes(entry_name)
            doc = parse_str(canon_name, strict=strict, file_content=raw_buf)

        self._str_asts[key] = (canon_name, doc, None)
        self._removed_keys.discard(key)
        return doc

    def edit_ini(
        self,
        entry_name: str,
        mutator: Callable[[ConstructFile], None],
        *,
        strict: bool = False,
        format_options: FormatOptions | None = None,
    ) -> ConstructFile:
        """Open a `.ini`/`.inc` entry AST, run `mutator(doc)` in-place, and record format options."""
        doc = self.open_ini(entry_name, strict=strict)
        mutator(doc)
        key = _normalize_key(entry_name)
        canon_name, _, prev_opts = self._ini_asts[key]
        chosen_opts = format_options if format_options is not None else prev_opts
        self._ini_asts[key] = (canon_name, doc, chosen_opts)
        return doc

    def edit_str(
        self,
        entry_name: str,
        mutator: Callable[[StrDocument], None],
        *,
        strict: bool = False,
        format_options: FormatOptions | None = None,
    ) -> StrDocument:
        """Open a `.str` entry AST, run `mutator(doc)` in-place, and record format options."""
        doc = self.open_str(entry_name, strict=strict)
        mutator(doc)
        key = _normalize_key(entry_name)
        canon_name, _, prev_opts = self._str_asts[key]
        chosen_opts = format_options if format_options is not None else prev_opts
        self._str_asts[key] = (canon_name, doc, chosen_opts)
        return doc

    def format_entries(
        self,
        filter_pattern: str = "*",
        *,
        strict: bool = False,
        options: FormatOptions | None = None,
    ) -> list[str]:
        """Load and apply `FormatOptions` to all matching `.ini`, `.inc`, and `.str` entries."""
        self._ensure_open()
        opts = options if options is not None else FormatOptions()
        formatted_names: list[str] = []

        for entry in self._source_handle.get_entries():
            key = _normalize_key(entry.name)
            if key in self._removed_keys or not _matches_glob(entry.name, filter_pattern):
                continue

            lower = key
            if lower.endswith(".str"):
                doc = self.open_str(entry.name, strict=strict)
                self._str_asts[key] = (self._str_asts[key][0], doc, opts)
                formatted_names.append(self._str_asts[key][0])
            elif lower.endswith((".ini", ".inc")):
                doc = self.open_ini(entry.name, strict=strict)
                self._ini_asts[key] = (self._ini_asts[key][0], doc, opts)
                formatted_names.append(self._ini_asts[key][0])

        return formatted_names

    def apply_stage(self, stage: EntryStage, *, filter_pattern: str = "*", strict: bool = False) -> list[str]:
        """Apply a pluggable `EntryStage` to matching entries in the archive or overlay."""
        self._ensure_open()
        applied: list[str] = []

        for entry in self._source_handle.get_entries():
            key = _normalize_key(entry.name)
            if key in self._removed_keys:
                continue
            if not _matches_glob(entry.name, filter_pattern) or not stage.matches(entry.name):
                continue

            canon_name, raw_buf = self._read_source_bytes(entry.name)
            transformed = stage.apply(canon_name, raw_buf, strict=strict)
            self.put_bytes(canon_name, transformed)
            applied.append(canon_name)

        return applied

    def put_bytes(self, entry_name: str, data: Buffer) -> None:
        """Stage a raw binary or text payload for `entry_name` (replacing existing or adding new)."""
        self._ensure_open()
        if not entry_name:
            raise ValueError("Entry path cannot be empty.")
        canon_name = _normalize_archive_path(entry_name)
        key = _normalize_key(canon_name)
        self._ini_asts.pop(key, None)
        self._str_asts.pop(key, None)
        self._removed_keys.discard(key)
        self._raw_overrides[key] = (canon_name, bytes(data))

    def remove(self, entry_name: str) -> bool:
        """Mark `entry_name` as removed from the staged output."""
        self._ensure_open()
        key = _normalize_key(entry_name)
        existed = (
            key in self._base_entries_by_key
            or key in self._ini_asts
            or key in self._str_asts
            or key in self._raw_overrides
        ) and key not in self._removed_keys
        self._ini_asts.pop(key, None)
        self._str_asts.pop(key, None)
        self._raw_overrides.pop(key, None)
        if key in self._base_entries_by_key:
            self._removed_keys.add(key)
        return existed

    def _collect_staged_payloads(self) -> tuple[list[tuple[str, bytes]], list[str], list[str], list[str]]:
        """Build `(entry_name, utf8_or_raw_bytes)` pairs and classify modified, added, and removed entries."""
        self._ensure_open()
        staged_by_key: dict[str, tuple[str, bytes]] = {}
        modified: list[str] = []
        added: list[str] = []

        for key, (canon_name, doc, opts) in self._ini_asts.items():
            rendered = doc.print() if opts is None else doc.print(opts)
            staged_by_key[key] = (canon_name, rendered.encode("utf-8"))
            if key in self._base_entries_by_key:
                modified.append(canon_name)
            else:
                added.append(canon_name)

        for key, (canon_name, doc, opts) in self._str_asts.items():
            rendered = doc.print() if opts is None else doc.print(opts)
            staged_by_key[key] = (canon_name, rendered.encode("utf-8"))
            if key in self._base_entries_by_key:
                modified.append(canon_name)
            else:
                added.append(canon_name)

        for key, (canon_name, buf) in self._raw_overrides.items():
            staged_by_key[key] = (canon_name, buf)
            if key in self._base_entries_by_key:
                modified.append(canon_name)
            else:
                added.append(canon_name)

        removed = [
            _normalize_archive_path(self._base_entries_by_key[k][0])
            for k in sorted(self._removed_keys)
            if k in self._base_entries_by_key
        ]
        return list(staged_by_key.values()), sorted(modified), sorted(added), removed

    def to_patch_memory(
        self,
        progress_callback: Callable[[_big.ProgressReport], bool | None] | None = None,
    ) -> bytes:
        """Serialize only modified and added entries into a standalone BIG4 patch buffer."""
        staged_pairs, _, _, _ = self._collect_staged_payloads()
        return pack_to_memory(staged_pairs, progress_callback=progress_callback)

    def save_patch(
        self,
        output_file: str | os.PathLike[str],
        progress_callback: Callable[[_big.ProgressReport], bool | None] | None = None,
    ) -> TransformResult:
        """Write a standalone BIG4 patch containing modified and added entries atomically to disk."""
        _, modified, added, removed = self._collect_staged_payloads()
        patch_bytes = self.to_patch_memory(progress_callback=progress_callback)
        dest = _write_atomic_bytes(output_file, patch_bytes)
        logger.info("Wrote pipeline delta patch to %s (%d bytes)", dest.resolve(), len(patch_bytes))
        return TransformResult(
            modified_entries=modified,
            added_entries=added,
            removed_entries=removed,
            output_bytes=None,
            output_path=dest,
        )

    def to_memory(
        self,
        progress_callback: Callable[[_big.ProgressReport], bool | None] | None = None,
    ) -> bytes:
        """Serialize the full merged archive (unchanged base entries + staged edits/additions) into memory."""
        staged_pairs, _, _, _ = self._collect_staged_payloads()
        staged_map = {_normalize_key(name): (name, buf) for name, buf in staged_pairs}

        merged: list[tuple[str, bytes]] = []
        for entry in self._source_handle.get_entries():
            key = _normalize_key(entry.name)
            if key in self._removed_keys:
                continue
            if key in staged_map:
                merged.append(staged_map.pop(key))
            else:
                merged.append((_normalize_archive_path(entry.name), self._source_handle.read_entry(entry.name)))

        merged.extend(staged_map.values())
        return pack_to_memory(merged, progress_callback=progress_callback)

    def save(
        self,
        output_file: str | os.PathLike[str],
        progress_callback: Callable[[_big.ProgressReport], bool | None] | None = None,
    ) -> TransformResult:
        """Write the full merged BIG4 archive atomically to `output_file`."""
        _, modified, added, removed = self._collect_staged_payloads()
        archive_bytes = self.to_memory(progress_callback=progress_callback)
        dest = _write_atomic_bytes(output_file, archive_bytes)
        logger.info("Wrote transformed archive to %s (%d bytes)", dest.resolve(), len(archive_bytes))
        return TransformResult(
            modified_entries=modified,
            added_entries=added,
            removed_entries=removed,
            output_bytes=None,
            output_path=dest,
        )


def transform_archive(
    source: ArchiveInput,
    output_file: str | os.PathLike[str] | None = None,
    *,
    transforms: Mapping[str, Callable[[ConstructFile], None]] | None = None,
    stages: Sequence[EntryStage] | None = None,
    filter_pattern: str | None = None,
    format_options: FormatOptions | None = None,
    strict: bool = False,
    patch_only: bool = False,
    progress_callback: Callable[[_big.ProgressReport], bool | None] | None = None,
) -> TransformResult:
    """
    Execute an in-memory archive-to-AST transformation pipeline and return a `TransformResult`.

    Parameters
    ----------
    source : str | os.PathLike[str] | BigArchive | BigOverlay
        Source `.big` file path, open `BigArchive`, or open `BigOverlay`.
    output_file : str | os.PathLike[str] | None, default=None
        Optional output `.big` file path written atomically. When `None`, serialized
        bytes are returned in `TransformResult.output_bytes`.
    transforms : Mapping[str, Callable[[ConstructFile], None]] | None, default=None
        Mapping of `{entry_name: mutator_fn}` applied to matching `.ini`/`.inc` ASTs.
    stages : Sequence[EntryStage] | None, default=None
        Optional ordered sequence of pluggable `EntryStage` transformations.
    filter_pattern : str | None, default=None
        Optional glob pattern for batch formatting or `EntryStage` application.
    format_options : FormatOptions | None, default=None
        Optional `FormatOptions` applied during AST serialization.
    strict : bool, default=False
        Whether to enforce strict structural parsing on `.ini`/`.inc`/`.str` entries.
    patch_only : bool, default=False
        If True, serializes only modified and added entries into a delta patch `.big`.
    progress_callback : Callable[[ProgressReport], bool | None] | None, default=None
        Optional progress/cancellation callback forwarded to packing.

    Returns
    -------
    TransformResult
        Summary of modified/added/removed entries and either `output_bytes` or `output_path`.
    """
    with ArchiveEditor(source) as editor:
        if transforms:
            for entry_name, mutator in transforms.items():
                editor.edit_ini(entry_name, mutator, strict=strict, format_options=format_options)

        if stages:
            for stage in stages:
                editor.apply_stage(stage, filter_pattern=filter_pattern or "*", strict=strict)
        elif filter_pattern is not None:
            editor.format_entries(filter_pattern, strict=strict, options=format_options)
        elif format_options is not None and not transforms:
            editor.format_entries("*", strict=strict, options=format_options)

        _, modified, added, removed = editor._collect_staged_payloads()

        if output_file is not None:
            if patch_only:
                return editor.save_patch(output_file, progress_callback=progress_callback)
            return editor.save(output_file, progress_callback=progress_callback)

        payload = (
            editor.to_patch_memory(progress_callback=progress_callback)
            if patch_only
            else editor.to_memory(progress_callback=progress_callback)
        )
        return TransformResult(
            modified_entries=modified,
            added_entries=added,
            removed_entries=removed,
            output_bytes=payload,
            output_path=None,
        )
