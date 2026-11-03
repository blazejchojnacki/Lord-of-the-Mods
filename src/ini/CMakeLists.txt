# @file src/ini/CMakeLists.txt
# @brief CMake for INI, INC, and STR parsing features
#
# Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
# Part of the Lord of the Mods (lotm) project.
# SPDX-License-Identifier: GPL-3.0-or-later

add_library(lotm_ini STATIC
    parser.cpp
)

set_target_properties(lotm_ini PROPERTIES
    POSITION_INDEPENDENT_CODE ON
)

target_compile_options(lotm_ini PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4 /permissive->
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall -Wextra -Wpedantic>
)

target_include_directories(lotm_ini PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include
)

target_link_libraries(lotm_ini PUBLIC lotm_core)
