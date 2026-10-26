/**
 * @file src/cppy_bridge/register.hpp
 * @brief header file to link feature specific binding cpp files to main binding file
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <nanobind/nanobind.h>
#include <vector>
#include <functional>

namespace lotm::python {

    using InitFn = std::function<void(nanobind::module_&)>;

    inline std::vector<InitFn>& get_registry() {
        static std::vector<InitFn> registry;
        return registry;
    }

    struct BindingRegistrar {
        explicit BindingRegistrar(InitFn fn) {
            get_registry().push_back(std::move(fn));
        }
    };

} // namespace lotm::python
