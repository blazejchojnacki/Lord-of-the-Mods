# @file tests/CMakeLists.txt
# @brief CMake for CPP testing
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

cmake_minimum_required(VERSION 3.20)
project(lotm_tests LANGUAGES CXX)

include(FetchContent)

FetchContent_Declare(
    Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG        v3.5.2
)
FetchContent_MakeAvailable(Catch2)

add_executable(lotm_cpp_tests
    cpp/main.cpp
    cpp/core/test_endian.cpp
   # cpp/test_big_archive.cpp
   # cpp/test_big_packer.cpp
)

target_link_libraries(lotm_cpp_tests PRIVATE
    lotm_core
   # lotm_big
    Catch2::Catch2
)

target_compile_features(lotm_cpp_tests PRIVATE cxx_std_20)

include(CTest)
include(Catch)
catch_discover_tests(lotm_cpp_tests)
