# @file tools/CMakeLists.txt
# @brief Developer and verification tools
#
# Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
# Part of the Lord of the Mods (lotm) project.
# SPDX-License-Identifier: GPL-3.0-or-later

add_executable(lotm_ini_validator
    ini_validator.cpp
    ../src/ini/parser.cpp
)

target_include_directories(lotm_ini_validator PRIVATE ../include)
target_compile_features(lotm_ini_validator PRIVATE cxx_std_20)

# cmake -B build -G Ninja -DLOTM_BUILD_TOOLS=ON
# ninja -C build lotm_ini_validator
