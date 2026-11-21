# @file ./CMakeLists.txt
# @brief main CMake
#
# Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
# Part of the Lord of the Mods (lotm) project.
# SPDX-License-Identifier: GPL-3.0-or-later

cmake_minimum_required(VERSION 3.20)

set(_lotm_fallback_version "0.6.0")
set(_lotm_pyproject "${CMAKE_CURRENT_SOURCE_DIR}/pyproject.toml")

if(EXISTS "${_lotm_pyproject}")
    file(STRINGS "${_lotm_pyproject}" _lotm_ver_lines
        REGEX "^[ \t]*version[ \t]*=[ \t]*\"[0-9]+\\.[0-9]+\\.[0-9]+([a-zA-Z0-9._-]*)?\""
    )
    if(_lotm_ver_lines)
        list(GET _lotm_ver_lines 0 _lotm_ver_line)
        string(REGEX REPLACE "^[^\"]*\"([^\"]+)\".*$" "\\1" _lotm_pkg_version "${_lotm_ver_line}")
    endif()
endif()

if(NOT _lotm_pkg_version)
    set(_lotm_pkg_version "${_lotm_fallback_version}")
endif()

# CMake project(...) requires numeric MAJOR.MINOR.PATCH
string(REGEX MATCH "^[0-9]+\\.[0-9]+\\.[0-9]+" _lotm_cmake_version "${_lotm_pkg_version}")
if(NOT _lotm_cmake_version)
    set(_lotm_cmake_version "${_lotm_fallback_version}")
endif()

project(Lord_of_the_Mods
    VERSION "${_lotm_cmake_version}"
    LANGUAGES CXX
)

add_compile_definitions(LOTM_VERSION_STRING="${_lotm_pkg_version}")

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

# Require Python and nanobind before processing subdirectories
set(Python_FIND_VIRTUALENV FIRST)
set(Python_FIND_REGISTRY NEVER)
find_package(Python 3.12 COMPONENTS Interpreter Development.Module Development.SABIModule REQUIRED)

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
add_subdirectory(src/bindings)
add_subdirectory(src/ini)


# tests
option(BUILD_TESTING "Build the test suite" OFF)

if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif()

# tools
option(LOTM_BUILD_TOOLS "Build internal development and verification tools" OFF)
if(LOTM_BUILD_TOOLS)
    add_subdirectory(tools)
endif()
