# Lord-of-the-Mods
# coverage-log

## 0.6.0 - 2026-11-21

```text
================================= tests coverage ==================================
_________________ coverage: platform win32, python 3.12.3-final-0 _________________

Name                            Stmts   Miss  Cover   Missing
-------------------------------------------------------------
src\lotm\__init__.py                6      0   100%
src\lotm\__main__.py                1      0   100%
src\lotm\big\__init__.py           17      0   100%
src\lotm\big\__main__.py            1      0   100%
src\lotm\big\_paths.py              5      0   100%
src\lotm\big\cli.py               104      0   100%
src\lotm\big\differ.py             41      0   100%
src\lotm\big\overlay.py            23      0   100%
src\lotm\big\packer.py             37      0   100%
src\lotm\big\unpacker.py           22      0   100%
src\lotm\cli.py                    30      0   100%
src\lotm\ini\__init__.py           26      0   100%
src\lotm\ini\cli.py                82      0   100%
src\lotm\ini\diagnostics.py        65      0   100%
src\lotm\ini\formatter.py          28      0   100%
src\lotm\ini\parser.py             29      0   100%
src\lotm\pipeline\__init__.py       3      0   100%
src\lotm\pipeline\editor.py       260      0   100%
src\lotm\pipeline\stages.py        49      0   100%
-------------------------------------------------------------
TOTAL                             829      0   100%
```

```text
Cpp coverage at 95%.
Name                                               Total lines    Coverage    Missing
--------------------------------------------------------------------------------------
Lord-of-the-Mods\build\tests\lotm_big_tests.exe           1112         94%
Lord-of-the-Mods\build\tests\lotm_ini_tests.exe           1881         96%
Lord-of-the-Mods\src\ini\file_io.cpp                       173         82%    60, 100, 110, 124, 184, 215-216, 219-220, 234-235, 247-249, 262-266, 268-269, 271-273, 275-278, 280-281, 320
Lord-of-the-Mods\src\big\big_diff.cpp                      246         88%    149, 197-199, 223, 225-231, 246, 256, 267, 283, 288, 290-294, 296-297, 299, 355, 366, 376, 394
Lord-of-the-Mods\include\ini\schema.hpp                     72         93%    80-81, 83-84, 159
Lord-of-the-Mods\src\big\big_archive.cpp                   288         93%    46, 55, 85, 107, 127, 242, 247, 256, 265, 272, 293, 296, 302, 308, 393, 403, 439, 451, 456, 483
Lord-of-the-Mods\src\ini\include_resolver.cpp               38         95%    66, 92
Lord-of-the-Mods\src\big\big_overlay.cpp                   101         96%    170-173
Lord-of-the-Mods\src\ini\ini_parser.cpp                    356         96%    51, 473, 505-512, 514-515, 523, 620
Lord-of-the-Mods\include\ini\ast.hpp                       233         97%    148-149, 151, 225, 229, 239-240, 242
Lord-of-the-Mods\include\core\string_utils.hpp              50         98%    95
Lord-of-the-Mods\src\big\big_packer.cpp                    302         98%    222, 271, 278, 285, 359, 417, 472
Lord-of-the-Mods\src\ini\ast.cpp                           317         98%    47, 72, 118-119, 121
Lord-of-the-Mods\src\ini\serializer.cpp                    286         98%    61, 72, 126-127, 130-131, 173
Lord-of-the-Mods\include\core\path_utils.hpp                94         99%    158
Lord-of-the-Mods\src\ini\str_parser.cpp                    115         99%    144
Lord-of-the-Mods\include\big\big_archive.hpp                 4        100%
Lord-of-the-Mods\include\big\big_diff.hpp                    3        100%
Lord-of-the-Mods\include\big\big_overlay.hpp                 2        100%
Lord-of-the-Mods\include\big\big_packer.hpp                  1        100%
Lord-of-the-Mods\include\core\endian.hpp                    21        100%
Lord-of-the-Mods\include\ini\lexer.hpp                     120        100%
Lord-of-the-Mods\include\ini\parser.hpp                     17        100%
Lord-of-the-Mods\src\ini\parser_utils.hpp                   10        100%
--------------------------------------------------------------------------------------
TOTAL                                                     2849         95%

Remaining 5% C++ consists of unmockable OS/hardware I/O faults (e.g., sudden disk space exhaustion during `out_file.write()`, physical read truncations) which are exempt from unit testing.
```

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
src\lotm\ini\__init__.py        22      0   100%
src\lotm\ini\cli.py             74      0   100%
src\lotm\ini\diagnostics.py     62      0   100%
src\lotm\ini\formatter.py       21      0   100%
src\lotm\ini\parser.py          24      0   100%
----------------------------------------------------------
TOTAL                          510      0   100%
```

```text
Cpp coverage at 95%.
Name                              Total lines    Coverage    Missing
---------------------------------------------------------------------
build\tests\lotm_big_tests.exe           1221         93%
build\tests\lotm_ini_tests.exe           1151         97%
src\big\big_diff.cpp                      331         90%    108, 170, 218-220, 244, 246-252, 299, 309, 320, 336, 341, 343-347, 349-350, 352, 418, 462, 473, 483, 488, 504, 526, 533
src\big\big_overlay.cpp                   131         93%    191-196, 199-201
include\ini\schema.hpp                     66         94%    73-74, 76-77
src\big\big_archive.cpp                   384         94%    45, 99, 167, 197, 219, 239, 365, 370, 379, 391, 399, 404, 421, 424, 430, 436, 521, 531, 538, 571, 583, 588, 615
src\big\big_packer.cpp                    345         97%    76, 245, 305, 363, 384, 403, 410, 476, 531
src\ini\parser.cpp                        781         97%    77, 87, 101, 163, 178, 218, 276-277, 280-281, 295-296, 307-309, 650, 767, 1012, 1133-1134, 1171, 1326-1329, 1337, 1346
include\ini\lexer.hpp                     145         99%    51-52
include\big\big_archive.hpp                 4        100%
include\big\big_diff.hpp                    3        100%
include\big\big_overlay.hpp                 2        100%
include\core\endian.hpp                    21        100%
include\ini\ast.hpp                       129        100%
include\ini\parser.hpp                     30        100%
---------------------------------------------------------------------
TOTAL                                    2372         95%

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
