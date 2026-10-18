# Gemini Pro 3.1

cmake_minimum_required(VERSION 3.20)
project(Lord_of_the_Mods VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Require Python and nanobind before processing subdirectories
find_package(Python 3.11 COMPONENTS Interpreter Development.Module REQUIRED)
find_package(nanobind CONFIG REQUIRED)

# # Modular targets: each folder handles its own sources and includes
add_subdirectory(src/big)
add_subdirectory(src/cppy_bridge)
