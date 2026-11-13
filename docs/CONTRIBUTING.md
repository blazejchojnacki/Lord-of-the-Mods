# Lord-of-the-Mods
# Contributing guide

This guide describes the golden path to configure, build, and test Lord of the Mods from source.

## 1. Initial Setup

Run these steps when setting up the project on a new machine.

**Prerequisites:**
* Windows 11 (x64)
* Ninja 1.10+
* x64 Native Tools Command Prompt (`vcvars64.bat`)
* CMake 3.20+
* Python 3.12+

**Repository & Environment Setup:**

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
pip install nanobind scikit-build-core mypy build
```

## 2. Development Workflow

When modifying C++ or Python source files, execute the following from the **x64 Native Tools Command Prompt**. We enforce **Ninja** to ensure clean, single-configuration directories.

1. Configure CMake
Build in `Debug` mode for active development and coverage profiling so MSVC generates PDB debug symbols.
```cmd
cmake -B build -S . -G Ninja -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON
```
or use `Release` when benchmarking or building distribution wheels.
```cmd
cmake -B build -S . -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
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

## 3. Testing & Coverage

Pull requests modifying core logic must maintain ≥ 85% test coverage. Always run both test suites locally before committing.

### Python (Pytest)
Run the integration test suite and generate a terminal coverage report:
```cmd
python -m pytest tests/python -v --cov=lotm --cov-report=term-missing
```

### C++ (Catch2 & OpenCppCoverage)
Run the native C++ unit tests. CTest is recommended for a quick pass/fail summary across both `lotm_cpp_tests` and `lotm_ini_tests`:
```cmd
ctest --test-dir build --output-on-failure
```
*(Note: To run specific tests or see detailed assertions, execute the binaries directly: `.\build\tests\lotm_cpp_tests.exe` and `.\build\tests\lotm_ini_tests.exe`)*

**C++ Coverage Generation:**
To generate the line-by-line HTML coverage report (requires `winget install OpenCppCoverage.OpenCppCoverage`). Ensure the project was compiled with `-DCMAKE_BUILD_TYPE=Debug` so that MSVC outputs PDB symbols for OpenCppCoverage:
```cmd
OpenCppCoverage.exe --sources "%CD%\src" --sources "%CD%\include" --excluded_sources "%CD%\tests" --export_type html:coverage_cpp -- "%CD%\build\tests\lotm_cpp_tests.exe"
```
```cmd
OpenCppCoverage.exe --sources "%CD%\src" --sources "%CD%\include" --excluded_sources "%CD%\tests" --export_type html:coverage_ini_cpp -- "%CD%\build\tests\lotm_ini_tests.exe"
```
```cmd
start .\coverage_cpp\index.html
```

## 4. Validating Type Stubs (.pyi)

Type stubs for the native C++ extension (`src/lotm/_core.pyi`) are maintained directly in the repository to provide precise IDE autocomplete and strict typing. Validate them using Mypy:

```cmd
python -m mypy src/lotm
```
Ensure the marker file exists so Python recognizes the package as typed:
```cmd
type nul > src\lotm\py.typed
```

## 5. Building Distribution Wheels

To compile the self-contained `.whl` package containing the C++ binary and stub definitions for a release:
```cmd
python -m build --wheel
```
The resulting package is stored inside the `dist/` directory.

## 6. Architecture & Targets

The build system is organized into decoupled CMake targets:
- `lotm_core`: Header-only interface library containing endian-swapping utilities (`endian.hpp`).
- `lotm_big`: Static C++ library implementing `BigArchive`, `BigPacker`, `BigDiff`, and `BigOverlay`.
- `lotm_ini`: Static C++ library implementing the zero-copy SAGE `.ini`, `.inc`, and `.str` lexer, schema tables, AST parser, iterative serializer, and `#include` virtual chroot validator.
- `_core`: The native Python extension module (`.pyd`) exported via `nanobind` under `lotm._core`.
