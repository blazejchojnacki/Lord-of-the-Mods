# Building from Source (Developers Only)

## Prerequisites:
	- Windows 11
	- Visual Studio 2022
	- MSVC v143+
	- x64 Developer Command Prompt (`vcvars64.bat`)
	- CMake 3.20+
	- Python 3.12+

```cmd
git clone [https://github.com/blazejchojnacki/Lord-of-the-Mods.git](https://github.com/blazejchojnacki/Lord-of-the-Mods.git)
cd Lord-of-the-Mods
pip install .
```

* **CMake Targets Structure:**
  * `lotm_core`: Header-only interface library (`endian.hpp`).
  * `lotm_big`: Static library for BIG archive format operations.
  * `lotm`: Shared Python extension module (`.pyd`) linked via `nanobind`.
* **Clean Rebuild Cycle:** The exact command sequence to reconfigure CMake, build native targets, and run tests.


## Generating Stubs with nanobind (.pyi)
Install nanobind-stubgen:
```
pip install nanobind-stubgen
```

Run the generator against the installed module:
```
python -m nanobind_stubgen -o src lotm
```

## Generating wheel:
```
python -m build --wheel
```
