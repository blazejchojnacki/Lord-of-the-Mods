# Developers manual

This guide describes how to configure, build, and test Lord of the Mods from source.

## Prerequisites:
	- Windows 11 (x64)
	- Visual Studio 2022 (MSVC v143 toolset with C++20 standard library)
	- x64 Developer Command Prompt (`vcvars64.bat`)
	- CMake 3.20+
	- Python 3.12+

## Repository Setup

Clone the repository and initialize the working tree:

```cmd
git clone [https://github.com/blazejchojnacki/Lord-of-the-Mods.git](https://github.com/blazejchojnacki/Lord-of-the-Mods.git)
```

```cmd
cd Lord-of-the-Mods
```

Create and activate a virtual environment:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install --upgrade pip
pip install nanobind scikit-build-core nanobind-stubgen build
```

## Architecture & Targets
The build system is organized into decoupled CMake targets:

	- `lotm_core`: Header-only interface library containing endian-swapping utilities (endian.hpp).

	- `lotm_big`: Static C++ library implementing BigArchive (reading) and BigPacker (writing).

	- `lotm`: The native Python extension module (.pyd) exported via nanobind.

## Clean Rebuild Cycle

When modifying C++ source files or CMake configurations, execute the following from the x64 Native Tools Command Prompt:

	1. Configure
``` cmd
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
```
	2. Compile
``` cmd
cmake --build build --config Release
```
	3. Local In-Place Testing

Point PYTHONPATH directly to the compiled extension to test changes without reinstalling:
``` cmd
set PYTHONPATH=%CD%\build\src\cppy_bridge
python -c "import lotm; print(dir(lotm.big))"
```

## Generating Type Stubs with nanobind (.pyi)

To provide autocomplete and parameter definitions for IDEs (like PyCharm and VS Code), generate the stubs using nanobind-stubgen:

Install nanobind-stubgen:

```
pip install nanobind-stubgen
```

Run the generator against the installed module:
```
python -m nanobind_stubgen -o src lotm
```
Ensure the marker file exists so Python recognizes the package as typed:
```
type nul > src\lotm\py.typed
```

## Building Distribution Wheels

Compile the self-contained .whl package containing the C++ binary and stub definitions:

```
python -m build --wheel
```
The resulting package is stored inside the dist/ directory.
