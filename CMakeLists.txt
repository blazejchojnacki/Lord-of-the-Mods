# @file ./CMakeLists.txt
# @brief main CMake
#
# Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
# Part of the Lord of the Mods (lotm) project.
# SPDX-License-Identifier: GPL-3.0-or-later

cmake_minimum_required(VERSION 3.20)
project(Lord_of_the_Mods VERSION 0.3.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Require Python and nanobind before processing subdirectories
find_package(Python 3.12 COMPONENTS Interpreter Development.Module REQUIRED)

# Automatically resolve nanobind CMake directory if not explicitly provided
if (NOT nanobind_DIR AND NOT DEFINED ENV{nanobind_DIR})
    execute_process(
        COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
        OUTPUT_STRIP_TRAILING_WHITESPACE
        OUTPUT_VARIABLE _nb_cmake_dir
        RESULT_VARIABLE _nb_status
    )
    if (_nb_status EQUAL 0 AND EXISTS "${_nb_cmake_dir}")
        set(nanobind_DIR "${_nb_cmake_dir}" CACHE PATH "Path to nanobind CMake config" FORCE)
    else()
        message(FATAL_ERROR "Failed to retrieve nanobind CMake directory from ${Python_EXECUTABLE}. Ensure nanobind is installed in the active environment.")
    endif()
endif()

find_package(nanobind CONFIG REQUIRED)

# # Modular targets: each folder handles its own sources and includes
add_subdirectory(src/core)
add_subdirectory(src/big)
add_subdirectory(src/cppy_bridge)


# tests
option(BUILD_TESTING "Build the test suite" ON)

if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif()
