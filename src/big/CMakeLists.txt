# @file src/big/CMakeLists.txt
# @brief CMake for BIG features
#
# Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
# Part of the Lord of the Mods (lotm) project.
# SPDX-License-Identifier: GPL-3.0-or-later

add_library(lotm_big STATIC
    big_archive.cpp
    big_packer.cpp
    big_diff.cpp
    big_overlay.cpp
)

set_target_properties(lotm_big PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>"
)

target_compile_options(lotm_big PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4 /permissive->
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall -Wextra -Wpedantic>
)

target_include_directories(lotm_big PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include
)

target_link_libraries(lotm_big PUBLIC lotm_core)
