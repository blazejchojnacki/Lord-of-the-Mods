# @file src/big/CMakeLists.txt
# @brief CMake for BIG features
#
# Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
# Part of the Lord of the Mods (lotm) project.
# SPDX-License-Identifier: GPL-3.0-or-later

add_library(lotm_big STATIC
    big_unpack.cpp
    big_pack.cpp
)

target_include_directories(lotm_big PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include
)

target_link_libraries(lotm_big PUBLIC lotm_core)
