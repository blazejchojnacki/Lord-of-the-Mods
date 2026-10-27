/**
 * @file src/cppy_bridge/main.cpp
 * @brief main binding between CPP and Python.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <nanobind/nanobind.h>
#include "register.hpp"

NB_MODULE(_core, m) {
    for (const auto& init_fn : lotm::python::get_registry()) {
        init_fn(m);
    }
}
