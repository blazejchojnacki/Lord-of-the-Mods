# Lord-of-the-Mods (lotm)

A high-performance C++20 and Python toolkit designed for modding EA *The Battle for Middle-earth* games.

## Features
- **Fast BIG4 Unpacking:** extract `.big` archives.
- **Byte-Fidelity Repacking:** Creates SAGE-compliant `.big` archives with alphabetical binary-search index ordering and EA build tag alignment.
- **Python 3.12+ Bindings:** C++ performance accessible directly in Python via `nanobind`.

## Requirements
- Windows 11 (x64)
- Python 3.12+


## Installation and use

To use the Python library in your project, see `docs/LIBRARY.md`.

To build the library from source or contribute to development, see `docs/DEVELOPMENT.md`

## Additional documentation:

For deep technical details regarding the BIG4 binary layout and alignment, see `docs/BIG4_FORMAT.md`.

## License

This project is licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later). See the `LICENSE` file for the full license text.

## Acknowledgments

Developed with architectural and implementation assistance from Google Gemini.
