# @file src/core/CMakeLists.txt
# @brief CMake for shared features
#
# Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
# Part of the Lord of the Mods (lotm) project.
# SPDX-License-Identifier: GPL-3.0-or-later

add_library(lotm_core INTERFACE)

target_include_directories(lotm_core INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../../include>
    $<INSTALL_INTERFACE:include>
)

target_compile_features(lotm_core INTERFACE cxx_std_20)
