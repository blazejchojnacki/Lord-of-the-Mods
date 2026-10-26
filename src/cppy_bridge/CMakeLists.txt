# @file src/cppy_bridge/CMakeLists.txt
# @brief CMake for CPP - Python binding
#
# Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
# Part of the Lord of the Mods (lotm) project.
# SPDX-License-Identifier: GPL-3.0-or-later

nanobind_add_module(lotm
    NB_STATIC
    main.cpp
    bind_big.cpp
)

target_include_directories(lotm PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include
)

target_link_libraries(lotm PRIVATE lotm_big)

install(TARGETS lotm LIBRARY DESTINATION .)
install(
    FILES
        ${CMAKE_CURRENT_SOURCE_DIR}/../lotm/__init__.pyi
        ${CMAKE_CURRENT_SOURCE_DIR}/../lotm/big.pyi
        ${CMAKE_CURRENT_SOURCE_DIR}/../lotm/py.typed
    DESTINATION lotm
)
