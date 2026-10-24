/**
 * @file tests/cpp/main.cpp
 * @brief Catch2 custom test runner entry point.
 *
 * Copyright (C) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_session.hpp>

int main(int argc, char* argv[]) {
    // Global setup logic (e.g., initializing a mock filesystem or logs) can go here

    int result = Catch::Session().run(argc, argv);

    // Global teardown logic can go here

    return result;
}
