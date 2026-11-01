# Lord-of-the-Mods (lotm)

[![PyPI version](https://img.shields.io/pypi/v/lord-of-the-mods.svg?color=blue)](https://pypi.org/project/lord-of-the-mods/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows_x64-0078D6.svg?logo=windows&logoColor=white)](https://www.microsoft.com/windows/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Code Style](https://img.shields.io/badge/C%2B%2B-20-00599C.svg?logo=cplusplus&logoColor=white)](https://en.cppreference.com/w/cpp/20)
[![Python Coverage](https://img.shields.io/badge/coverage--python-100%25-brightgreen)](https://github.com/blazejchojnacki/Lord-of-the-Mods/blob/main/docs/coverage-log.md)
[![C++ Coverage](https://img.shields.io/badge/coverage--c%2B%2B-95%25-brightgreen)](https://github.com/blazejchojnacki/Lord-of-the-Mods/blob/main/docs/coverage-log.md)

A high-performance C++20 and Python toolkit designed for modding EA *The Battle for Middle-earth* games.

## Features
- **Fast BIG4 Unpacking:** Extract `.big` archives with strict security validation.
- **Byte-Fidelity Repacking:** Creates SAGE-compliant `.big` archives with alphabetical binary-search index ordering and EA build tag alignment.
- **Python 3.12+ Bindings:** C++ performance accessible directly in Python via `nanobind`.

## Requirements
- Windows 11 (x64)
- Python 3.12+

## Documentation
The `lotm` project provides comprehensive documentation for contributors and users:
* **[Python API Reference](https://github.com/blazejchojnacki/Lord-of-the-Mods/blob/main/docs/python-api.md)**: Programmatic extraction and packing APIs.
* **[Command-Line Tools](https://github.com/blazejchojnacki/Lord-of-the-Mods/blob/main/docs/cli.md)**: Standalone terminal instructions for `lotm-big-pack` and `lotm-big-unpack`.
* **[BIG4 Format Specs](https://github.com/blazejchojnacki/Lord-of-the-Mods/blob/main/docs/big4-format.md)**: Deep technical details regarding the BIG4 binary layout and SAGE engine alignment quirks.
* **[Contributing Guide](https://github.com/blazejchojnacki/Lord-of-the-Mods/blob/main/docs/CONTRIBUTING.md)**: Development, compilation, and testing workflows for C++ and Python.
* **[Coverage Log](https://github.com/blazejchojnacki/Lord-of-the-Mods/blob/main/docs/coverage-log.md)**: Current C++ Catch2 and Pytest coverage benchmarks.
* **[Changelog](https://github.com/blazejchojnacki/Lord-of-the-Mods/blob/main/docs/CHANGELOG.md)**: Release history and feature notes.

## Installation and use

Install the pre-compiled library via pip:
```cmd
pip install lord-of-the-mods
```

## Testing

Install the test dependencies and run the pytest suite against the editable C++ extension:

```cmd
pip install -e ".[test]"
```
```cmd
pytest tests/python -v
```

## License

This project is licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later). See the `LICENSE` file for the full license text.

## Acknowledgments

Developed with architectural and implementation assistance from Google Gemini.
