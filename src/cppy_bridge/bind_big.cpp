/**
 * @file src/cppy_bridge/bind_big.cpp
 * @brief Binding .BIG features
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

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/filesystem.h>
#include <nanobind/stl/vector.h>

#include "register.hpp"
#include <big/big_unpack.hpp>
#include <big/big_pack.hpp>

namespace nb = nanobind;

namespace lotm::python {

    void register_big_bindings(nb::module_& m) {
        auto sub = m.def_submodule("big", "BIG archive handling");

        nb::class_<lotm::big::BigEntry>(sub, "BigEntry")
            .def_ro("offset", &lotm::big::BigEntry::offset)
            .def_ro("size", &lotm::big::BigEntry::size)
            .def_ro("name", &lotm::big::BigEntry::name);

        nb::class_<lotm::big::BigArchive>(sub, "BigArchive")
            .def(nb::init<std::filesystem::path>(), nb::arg("file_path"))
            .def("read_header", &lotm::big::BigArchive::read_header)
            .def("extract_all", &lotm::big::BigArchive::extract_all, nb::arg("output_dir"))
            .def("get_entries", &lotm::big::BigArchive::get_entries);

        nb::class_<lotm::big::BigPacker>(sub, "BigPacker")
            .def_static("pack_from_directory", &lotm::big::BigPacker::pack_from_directory,
                nb::arg("source_dir"), nb::arg("output_file"));
    }

    // Static instance registers this function before NB_MODULE executes
    static BindingRegistrar big_registrar(&register_big_bindings);

} // namespace lotm::python
