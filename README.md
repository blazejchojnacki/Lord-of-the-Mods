# Lord-of-the-Mods (lotm)

[![PyPI version](https://img.shields.io/pypi/v/lord-of-the-mods.svg?color=blue)](https://pypi.org/project/lord-of-the-mods/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows_x64-0078D6.svg?logo=windows&logoColor=white)](https://www.microsoft.com/windows/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Code Style](https://img.shields.io/badge/C%2B%2B-20-00599C.svg?logo=cplusplus&logoColor=white)](https://en.cppreference.com/w/cpp/20)

A high-performance C++20 and Python toolkit designed for modding EA *The Battle for Middle-earth* games.

## Features
- **Fast BIG4 Unpacking:** extract `.big` archives.
- **Byte-Fidelity Repacking:** Creates SAGE-compliant `.big` archives with alphabetical binary-search index ordering and EA build tag alignment.
- **Python 3.12+ Bindings:** C++ performance accessible directly in Python via `nanobind`.

## Requirements
- Windows 11 (x64)
- Python 3.12+


## Installation and use

To use the Python library in your project, see **[Python Library Guide](https://github.com/blazejchojnacki/Lord-of-the-Mods/blob/main/docs/LIBRARY.md)**

To build the library from source or contribute to development, see **[Development Guide](https://github.com/blazejchojnacki/Lord-of-the-Mods/blob/main/docs/DEVELOPMENT.md)**

## Additional documentation:

For deep technical details regarding the BIG4 binary layout and alignment, see **[BIG4 Format Specs](https://github.com/blazejchojnacki/Lord-of-the-Mods/blob/main/docs/BIG4_FORMAT.md)**.

For a short guide on manual testing, see **[Manual Tests](https://github.com/blazejchojnacki/Lord-of-the-Mods/blob/main/tests/manual-tests.md)**

## License

This project is licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later). See the `LICENSE` file for the full license text.

## Acknowledgments

Developed with architectural and implementation assistance from Google Gemini.
