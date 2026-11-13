# Lord-of-the-Mods
# coverage-log

## 0.5.0 - 2026-11-13

```text
======================== tests coverage =========================
________ coverage: platform win32, python 3.12.3-final-0 ________

Name                         Stmts   Miss  Cover   Missing
----------------------------------------------------------
src\lotm\__init__.py             5      0   100%
src\lotm\__main__.py             1      0   100%
src\lotm\big\__init__.py        17      0   100%
src\lotm\big\__main__.py         1      0   100%
src\lotm\big\cli.py            102      0   100%
src\lotm\big\differ.py          57      0   100%
src\lotm\big\overlay.py         23      0   100%
src\lotm\big\packer.py          43      0   100%
src\lotm\big\unpacker.py        28      0   100%
src\lotm\cli.py                 30      0   100%
src\lotm\ini\__init__.py        20      0   100%
src\lotm\ini\cli.py             72      0   100%
src\lotm\ini\parser_api.py      85      0   100%
----------------------------------------------------------
TOTAL                          484      0   100%
```

```text
Cpp coverage at 95%.
Name                              Total lines    Coverage    Missing
---------------------------------------------------------------------
build\tests\lotm_cpp_tests.exe           1221         93%
build\tests\lotm_ini_tests.exe           1088         97%
src\big\big_diff.cpp                      331         90%    108, 170, 218-220, 244, 246-252, 299, 309, 320, 336, 341, 343-347, 349-350, 352, 418, 462, 473, 483, 488, 504, 526, 533
src\big\big_overlay.cpp                   131         93%    191-196, 199-201
include\ini\schema.hpp                     66         94%    73-74, 76-77
src\big\big_archive.cpp                   384         94%    45, 99, 167, 197, 219, 239, 365, 370, 379, 391, 399, 404, 421, 424, 430, 436, 521, 531, 538, 571, 583, 588, 615
src\big\big_packer.cpp                    345         97%    76, 245, 305, 363, 384, 403, 410, 476, 531
src\ini\parser.cpp                        766         97%    64, 74, 88, 159, 199, 257-258, 272-273, 284-286, 621, 737, 984, 1105-1106, 1143, 1298-1301, 1309, 1318
include\ini\lexer.hpp                     130         98%    51-52
include\big\big_archive.hpp                 4        100%
include\big\big_diff.hpp                    3        100%
include\big\big_overlay.hpp                 2        100%
include\core\endian.hpp                    21        100%
include\ini\parser.hpp                     27        100%
include\ini\types.hpp                      99        100%
---------------------------------------------------------------------
TOTAL                                    2309         95%

Remaining 5% C++ consists of unmockable OS/hardware I/O faults (e.g., sudden disk space exhaustion during `out_file.write()`, physical read truncations) which are exempt from unit testing.
```

## 0.4.0 - 2026-11-08

```text
================================= tests coverage ==================================
_________________ coverage: platform win32, python 3.12.3-final-0 _________________

Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
src\lotm\__init__.py           5      0   100%
src\lotm\__main__.py           1      0   100%
src\lotm\big\__init__.py      17      0   100%
src\lotm\big\__main__.py       1      0   100%
src\lotm\big\cli.py          102      0   100%
src\lotm\big\differ.py        57      0   100%
src\lotm\big\overlay.py       23      0   100%
src\lotm\big\packer.py        43      0   100%
src\lotm\big\unpacker.py      28      0   100%
src\lotm\cli.py               28      0   100%
--------------------------------------------------------
TOTAL                        305      0   100%
```

```text
Cpp coverage at 93%.
Name                              Total lines    Coverage
build\tests\lotm_cpp_tests.exe           1221         93%
src\big\big_diff.cpp                      331         89%
src\big\big_overlay.cpp                   131         93%
src\big\big_archive.cpp                   384         94%
src\big\big_packer.cpp                    345         97%
include\big\big_archive.hpp                 4        100%
include\big\big_diff.hpp                    3        100%
include\big\big_overlay.hpp                 2        100%
include\core\endian.hpp                    21        100%

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
