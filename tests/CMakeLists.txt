# @file tests/CMakeLists.txt
# @brief CMake for CPP testing
#
# Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
# Part of the Lord of the Mods (lotm) project.
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
    cpp/big/test_big_unpack.cpp
    cpp/big/test_big_pack.cpp
)

target_link_libraries(lotm_cpp_tests PRIVATE
    lotm_core
    lotm_big
    Catch2::Catch2
)

target_compile_features(lotm_cpp_tests PRIVATE cxx_std_20)

include(CTest)
include(Catch)
catch_discover_tests(lotm_cpp_tests)
