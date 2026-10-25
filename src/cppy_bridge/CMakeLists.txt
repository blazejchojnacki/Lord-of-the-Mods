# @file src/cppy_bridge/CMakeLists.txt
# @brief CMake for CPP - Python binding
#
# Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
# Part of the Lord of the Mods (lotm) project.
#
# This program is free software: you can redistribute it and/or modify
# 	it under the terms of the GNU General Public License as published by
# 	the Free Software Foundation, either version 3 of the License, or
# 	(at your option) any later version.
#
# 	This program is distributed in the hope that it will be useful,
# 	but WITHOUT ANY WARRANTY; without even the implied warranty of
# 	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# 	GNU General Public License for more details.
#
# 	You should have received a copy of the GNU General Public License
# 	along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
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
