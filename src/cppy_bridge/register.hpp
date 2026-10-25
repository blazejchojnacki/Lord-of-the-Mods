/**
 * @file src/cppy_bridge/register.hpp
 * @brief header file to link feature specific binding cpp files to main binding file
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
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
