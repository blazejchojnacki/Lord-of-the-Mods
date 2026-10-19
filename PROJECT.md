# Lord-of-the-Mods

## author:
Błażej Chojnacki
blazejchojnacki

# notes:
nanobind for Python - C++ bridge.

# features:
BIG archive extractor
BIG archive compressor

## possible upgrades:
1. Currently, the engine must extract the entire archive to disk.
Modding tools, diff inspectors, and patchers usually only need to read a single file (e.g., data\ini\armor.ini) directly into memory as a std::span<const uint8_t> or std::string without touching the disk.
2. Simulate mounting several overriding BIG by the game.
3. CSF file parser?
4. map decoder for object name updates, procedural changes accross multiple maps, Git tracking.

# structure:
lord-of-the-mods/
├── .gitignore
├── CMakeLists.txt                     # main CMake
├── pyproject.toml                     # scikit-build-core configuration
├── README.md
│
├── include/
│   ├── big/
│   │   ├── big_pack.hpp
│   │   ├── big_unpack.hpp
│   │   ├── types.hpp
│   │   └── ...
│   ├── core/
│   │   ├── endian.hpp
│   │   └── ...
│   └── ...
│
├── src/
│   ├── big/
│   │   ├── big_pack.cpp
│   │   ├── big_unpack.cpp
│   │   ├── CMakeLists.txt
│   │   └── ...
│   ├── core/
│   │   ├── CMakeLists.txt
│   │   └── ...
│   ├── cppy_bridge/
│   │   ├── big_bind.cpp
│   │   ├── register.hpp
│   │   ├── main.cpp
│   │   ├── CMakeLists.txt
│   │   └── ...
│   └── ...
|
├── scripts/
│   ├── big_pack.py
│   ├── big_unpack.py
│   └── ...
|
└── tests/
    ├── big-example/...
    ├── manual_test.md
    ├── (CMakeLists.txt)
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
