# @file src/cppy_bridge/CMakeLists.txt
# @brief CMake for CPP - Python binding
#
# Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
# Part of the Lord of the Mods (lotm) project.
# SPDX-License-Identifier: GPL-3.0-or-later

nanobind_add_module(_core
    NB_STATIC
    main.cpp
    bind_big.cpp
)

target_include_directories(_core PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include
)

target_link_libraries(_core PRIVATE lotm_big)

install(TARGETS _core LIBRARY DESTINATION lotm)
# Only install the compiled target; python files and stubs are handled by wheel.packages
