# Lord-of-the-Mods
# coverage-log

## 0.4.0 - 2026-11-05

```text
========================================================================= tests coverage =========================================================================
________________________________________________________ coverage: platform win32, python 3.12.3-final-0 _________________________________________________________

Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
src\lotm\__init__.py           4      0   100%
src\lotm\big\__init__.py      16      0   100%
src\lotm\big\cli.py           76      0   100%
src\lotm\big\differ.py        42      0   100%
src\lotm\big\overlay.py       23      0   100%
src\lotm\big\packer.py        29      0   100%
src\lotm\big\unpacker.py      19      0   100%
--------------------------------------------------------
TOTAL                        209      0   100%
```

```text
Cpp coverage at 98%.
Name                              Total lines    Coverage
build\tests\lotm_cpp_tests.exe           1470         98%
src\big\big_archive.cpp                   282         95%
src\big\big_diff.cpp                      112         96%
src\big\big_packer.cpp                    226         98%
src\ini\parser.cpp                        680         99%
include\big\big_archive.hpp                 3        100%
include\big\big_diff.hpp                    3        100%
include\big\big_overlay.hpp                 1        100%
include\core\endian.hpp                    21        100%
include\ini\parser.hpp                     14        100%
include\ini\types.hpp                      22        100%
src\big\big_overlay.cpp                   106        100%

Remaining 2% C++ consists of unmockable OS/hardware I/O faults (e.g., sudden disk space exhaustion during `out_file.write()`, physical read truncations) which are exempt from unit testing.
```


## 0.3.0 - 2026-11-03

```text
========================================================================= tests coverage =========================================================================
________________________________________________________ coverage: platform win32, python 3.12.3-final-0 _________________________________________________________

Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
src\lotm\__init__.py           4      0   100%
src\lotm\big\__init__.py      16      0   100%
src\lotm\big\cli.py           76      0   100%
src\lotm\big\differ.py        42      0   100%
src\lotm\big\overlay.py       23      0   100%
src\lotm\big\packer.py        29      0   100%
src\lotm\big\unpacker.py      19      0   100%
--------------------------------------------------------
TOTAL                        209      0   100%
```

```text
Cpp coverage at 97%.
Name                              Total lines    Coverage
build\tests\lotm_cpp_tests.exe            754         97%
src\big\big_archive.cpp                   282         95%
src\big\big_diff.cpp                      112         96%
src\big\big_packer.cpp                    226         98%
include\big\big_archive.hpp                 3        100%
include\big\big_diff.hpp                    3        100%
include\big\big_overlay.hpp                 1        100%
include\core\endian.hpp                    21        100%
src\big\big_overlay.cpp                   106        100%

Remaining 3% C++ consists of unmockable OS/hardware I/O faults (e.g., sudden disk space exhaustion during `out_file.write()`, physical read truncations) which are exempt from unit testing.
```



## 0.2.0 - 2026-11-01

```text
========================================================================= tests coverage =========================================================================
________________________________________________________ coverage: platform win32, python 3.12.3-final-0 _________________________________________________________

Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
src\lotm\__init__.py           4      0   100%
src\lotm\big\__init__.py      10      0   100%
src\lotm\big\cli.py           34      0   100%
src\lotm\big\packer.py        14      0   100%
src\lotm\big\unpacker.py      18      0   100%
--------------------------------------------------------
TOTAL                         80      0   100%
```

```text
Cpp coverage at 96%.
Name                              Total lines    Coverage
build\tests\lotm_cpp_tests.exe            375         96%
src\big\big_archive.cpp                   235         94%
src\big\big_packer.cpp                    116         97%
include\big\big_archive.hpp                 3        100%
include\core\endian.hpp                    21        100%

Remaining 4% C++ consists of unmockable OS/hardware I/O faults (e.g., sudden disk space exhaustion during `out_file.write()`, physical read truncations) which are exempt from unit testing.
```

## 0.1.0 - 2026-10

```text
========================================================================= tests coverage =========================================================================
________________________________________________________ coverage: platform win32, python 3.12.3-final-0 _________________________________________________________

Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
src\lotm\__init__.py           4      0   100%
src\lotm\big\__init__.py      10      0   100%
src\lotm\big\cli.py           34      0   100%
src\lotm\big\packer.py        14      0   100%
src\lotm\big\unpacker.py      18      0   100%
--------------------------------------------------------
TOTAL                         80      0   100%
```

```text
Cpp coverage at 95%.
Coverage    Total lines    Items
     95%            300    build\tests\lotm_cpp_tests.exe
     93%            161	   src\big\big_archive.cpp
     97%            116	   src\big\big_packer.cpp
    100%              2    include\big\big_archive.hpp
    100%             21	   include\core\endian.hpp

Remaining 5% C++ consists of unmockable OS/hardware I/O faults (e.g., sudden disk space exhaustion during `out_file.write()`, physical read truncations) which are exempt from unit testing.
```
