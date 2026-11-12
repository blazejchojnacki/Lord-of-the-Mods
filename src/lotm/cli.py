"""
@file src/lotm/cli.py
@brief Unified top-level command-line interface coordinator for Lord of the Mods (lotm)

Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
Part of the Lord of the Mods (lotm) project.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import NoReturn

from lotm import __version__
from lotm.big import cli as big_cli
from lotm.ini import cli as ini_cli

EXIT_SUCCESS = 0
EXIT_ERROR = 1


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the top-level umbrella ArgumentParser for lotm."""
    parser = argparse.ArgumentParser(
        prog="lotm",
        description="Lord of the Mods (lotm) — high-performance SAGE engine modding toolkit.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="domain", required=True)

    big_cli.register_subparser(subparsers)
    ini_cli.register_subparser(subparsers)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    Execute the unified lotm CLI coordinator with structured exception handling.

    Parameters
    ----------
    argv : Sequence[str] | None, default=None
        Command-line arguments (defaults to sys.argv[1:] when None).

    Returns
    -------
    int
        Process exit code (0 for success, 1 for runtime error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        handler: Callable[[argparse.Namespace], int] = args.handler
        return handler(args)
    except Exception as exc:
        subcmd = getattr(args, "command", None)
        label = f"{args.domain} {subcmd}" if subcmd else str(args.domain)
        print(f"Command '{label}' failed: {exc}", file=sys.stderr)
        return EXIT_ERROR


def cli_entry() -> NoReturn:
    """Console script entry point for pyproject.toml."""
    sys.exit(main())


if __name__ == "__main__":  # pragma: no cover
    cli_entry()
