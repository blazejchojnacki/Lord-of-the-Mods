# Lord-of-the-Mods
# Developers guide

This guide describes how to configure, build, and test Lord of the Mods from source.

## 1. Initial Setup (First Time Only)

Run these steps when setting up the project on a new machine.

### Prerequisites:
	- Windows 11 (x64)
	- Ninja 1.10+
	- x64 Native Tools Command Prompt (`vcvars64.bat`)
	- CMake 3.20+
	- Python 3.12+

### Repository Setup

Clone the repository and initialize the working tree:

```cmd
git clone https://github.com/blazejchojnacki/Lord-of-the-Mods.git
```

```cmd
cd Lord-of-the-Mods
```

Create and activate a virtual environment:

```cmd
python -m venv .venv
```
```cmd
.venv\Scripts\activate.bat
```
Install build dependencies:
```cmd
pip install --upgrade pip
```
```cmd
pip install nanobind scikit-build-core nanobind-stubgen build
```

## 2. After modifying C++ code

When modifying C++ source files or CMake configurations, execute the following from the x64 Native Tools Command Prompt. We enforce **Ninja** to ensure clean, single-configuration directories.

1. Configure CMake
```cmd
cmake -B build -S . -G Ninja -DCMAKE_BUILD_TYPE=Release
```
2. Compile the binary
```cmd
cmake --build build
```
3. Local In-Place Testing
Link the compiled extension directly into your virtual environment seamlessly:
```cmd
pip install -e ".[test]"
```

## 3. After modifing bindings - Generating Type Stubs (.pyi)

To provide autocomplete and parameter definitions for IDEs (like PyCharm and VS Code), generate the stubs using nanobind-stubgen:

Install nanobind-stubgen:
```cmd
pip install nanobind-stubgen
```

Run the generator against the installed module:
```cmd
python -m nanobind_stubgen -o src lotm
```
Ensure the marker file exists so Python recognizes the package as typed:
```cmd
type nul > src\lotm\py.typed
```

## 4. Building Distribution Wheels - for publishing a release

Compile the self-contained .whl package containing the C++ binary and stub definitions:

```cmd
python -m build --wheel
```
The resulting package is stored inside the `dist/` directory.

## 5. Quality Gates & Testing

* **Coverage Requirement:** Pull requests modifying core Python or C++ logic must maintain ≥ 85% test coverage.
* **Pre-Commit Validation:** Always run both test suites locally before submitting your code:
  * **Python:** `pytest tests/python -v`
  * **C++:** `ctest --test-dir build --output-on-failure`

## 6. Architecture & Targets
The build system is organized into decoupled CMake targets:

- `lotm_core`: Header-only interface library containing endian-swapping utilities (endian.hpp).
- `lotm_big`: Static C++ library implementing `BigArchive` (reading) and `BigPacker` (writing).
- `lotm`: The native Python extension module (.pyd) exported via nanobind.
