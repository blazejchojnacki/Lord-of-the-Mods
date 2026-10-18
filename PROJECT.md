# Lord-of-the-Mods

## author:
Błażej Chojnacki
blazejchojnacki

# notes:
nanobind for Python - C++ bridge.

# features:
BIG archive extractor
BIG archive compressor

# structure:
lord-of-the-mods/
├── CMakeLists.txt
├── pyproject.toml                     # scikit-build-core configuration
│
├── include/
│   └── ...
│
├── src/          
│   └── ...
└── tests/
    ├── CMakeLists.txt
    └── ...

# launch:
MS Visual Studio. Compiler MSVC
Terminal: x64 for CPP Py (cmd for x64)

```CMD
.venv\Scripts\activate.bat
```

```CMD
for /f "tokens=*" %i in ('python -m nanobind --cmake_dir') do set "NANOBIND_DIR=%i"
```

```CMD
cmake -B build -S . -Dnanobind_DIR="%NANOBIND_DIR%"
```

```CMD
cmake --build build --config Release
```

```CMD
set PYTHONPATH=%CD%\build\src\cppy_bridge
```

```CMD
python -c "import lotm; print(dir(lotm.big))"
```
