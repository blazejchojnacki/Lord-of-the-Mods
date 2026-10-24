# Lord-of-the-Mods
# C++ Test Suite Manual

This document details how to configure, compile, and execute the Catch2 native test suite for the `lotm` project.

## 1. Directory Structure

Ensure your test files are arranged according to the test runner architecture:

```text
Lord-of-the-Mods/
├── CMakeLists.txt
├── include/
├── src/
└── tests/
    ├── CMakeLists.txt
    └── cpp/
        ├── main.cpp
        └── core/
            └── test_endian.cpp
```

## 2. Compiling the Tests

Always execute these commands from the **x64 Native Tools Command Prompt** (`vcvars64.bat`):

### 1. Configure CMake with Testing Enabled
```cmd
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
```

### 2. Build Only the Test Executable
Instead of building all Python extensions, compile just the test target:
```cmd
cmake --build build --config Release --target lotm_cpp_tests
```

## 3. Running the Tests

### Method A: Direct Test Runner Execution (Recommended)
Running the test binary directly provides real-time, colored terminal feedback and full access to Catch2 CLI flags:

```cmd
.\build\tests\Release\lotm_cpp_tests.exe
```

### Method B: CTest Integration
To run the tests through CMake's test driver:

```cmd
ctest --test-dir build -C Release --output-on-failure
```

## 4. Catch2 CLI Command Reference

The test binary accepts filters, tag selectors, and output flags directly.

### Running Specific Tests by Tag
Run only the endianness tests:
```cmd
.\build\tests\Release\lotm_cpp_tests.exe [endian]
```

Run only compile-time `constexpr` verification:
```cmd
.\build\tests\Release\lotm_cpp_tests.exe [constexpr]
```

Exclude system routing tests:
```cmd
.\build\tests\Release\lotm_cpp_tests.exe ~[routing]
```

### Running Specific Tests by Name
Run tests matching a wildcard pattern:
```cmd
.\build\tests\Release\lotm_cpp_tests.exe "*Compile-time*"
```

### Detailed Output Flags
Show successful assertions as well as failures:
```cmd
.\build\tests\Release\lotm_cpp_tests.exe -s
```

List all available test cases without running them:
```cmd
.\build\tests\Release\lotm_cpp_tests.exe --list-tests
```

List all defined tags:
```cmd
.\build\tests\Release\lotm_cpp_tests.exe --list-tags
```
