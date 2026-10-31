# Lord-of-the-Mods
# C++ Test Suite Manual

This document details how to configure, compile, and execute the Catch2 native test suite and code coverage for the `lotm` project.

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

Always execute these commands from the **x64 Native Tools Command Prompt** (`vcvars64.bat`). We strictly enforce **Ninja** as the build generator to prevent configuration pollution.

### 1. Configure CMake with Testing Enabled
```cmd
cmake -B build -S . -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
```

### 2. Build Only the Test Executable
Instead of building all Python extensions, compile just the test target:
```cmd
cmake --build build --target lotm_cpp_tests
```

## 3. Running the Tests

### Method A: Direct Test Runner Execution (Recommended)
Running the test binary directly provides real-time, colored terminal feedback and full access to Catch2 CLI flags:

```cmd
.\build\tests\lotm_cpp_tests.exe
```

### Method B: CTest Integration
To run the tests through CMake's test driver:

```cmd
ctest --test-dir build --output-on-failure
```

## 4. Catch2 CLI Command Reference

The test binary accepts filters, tag selectors, and output flags directly.

*   Run tests by tag: `.\build\tests\lotm_cpp_tests.exe [endian]`
*   List available tests: `.\build\tests\lotm_cpp_tests.exe --list-tests`

---

## 5. C++ Code Coverage (OpenCppCoverage)

To verify internal test coverage thresholds, run OpenCppCoverage against the test binary.

**Prerequisites:**
```cmd
winget install OpenCppCoverage.OpenCppCoverage
```

**Generate Interactive HTML Report:**
Run the following command from the repository root to output a report into the `coverage_cpp` folder:

```cmd
OpenCppCoverage.exe --sources "%CD%\src" --sources "%CD%\include" --excluded_sources "%CD%\tests" --export_type html:coverage_cpp -- "%CD%\build\tests\lotm_cpp_tests.exe"
```

Open the report in your browser:
```cmd
start .\coverage_cpp\index.html
```

---

## 6. Python Integration Tests (Pytest)

The Python test suite (`tests/python/`) verifies the `nanobind` bindings, programmatic APIs, and CLI routing. 

**Execution:**
Run pytest from the repository root using the editable pip installation:
```cmd
pip install -e ".[test]"
pytest tests/python -v
```

**Coverage Measurement:**
To generate a Python coverage report and verify the 85% requirement:
```cmd
python -m pytest tests/python --cov=lotm --cov-report=term-missing
```
