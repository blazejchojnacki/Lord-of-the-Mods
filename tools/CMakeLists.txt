# @file tools/CMakeLists.txt
# @brief Developer and verification tools
#
# Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
# Part of the Lord of the Mods (lotm) project.
# SPDX-License-Identifier: GPL-3.0-or-later

add_executable(lotm_ini_validator
    ini_validator.cpp
)

target_link_libraries(lotm_ini_validator PRIVATE
    lotm_ini
)

target_compile_features(lotm_ini_validator PRIVATE cxx_std_20)

target_compile_options(lotm_ini_validator PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4 /permissive->
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall -Wextra -Wpedantic>
)

# cmake -B build -G Ninja -DLOTM_BUILD_TOOLS=ON
# ninja -C build lotm_ini_validator
