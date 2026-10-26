/**
 * @file src/cppy_bridge/bind_big.cpp
 * @brief Binding .BIG features
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
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

        nb::class_<lotm::big::BigEntry>(sub, "BigEntry", "Metadata record for an entry inside a BIG4 archive")
            .def_ro("offset", &lotm::big::BigEntry::offset, "Byte offset within archive")
            .def_ro("size", &lotm::big::BigEntry::size, "Size of uncompressed data in bytes")
            .def_ro("name", &lotm::big::BigEntry::name, "Internal path of the entry")
            .def("__repr__", [](const lotm::big::BigEntry& entry) {
            return "<BigEntry name='" + entry.name + "' size=" + std::to_string(entry.size) +
                " offset=" + std::to_string(entry.offset) + ">";
                });

        nb::class_<lotm::big::BigArchive>(sub, "BigArchive", "Parser and extractor for BIG4 archives")
            .def(nb::init<std::filesystem::path>(), nb::arg("file_path"),
                "Open a BIG archive from disk")
            .def("read_header", &lotm::big::BigArchive::read_header,
                nb::call_guard<nb::gil_scoped_release>(),
                "Parses and validates the archive header and index")
            .def("extract_all", &lotm::big::BigArchive::extract_all, nb::arg("output_dir"),
                nb::call_guard<nb::gil_scoped_release>(),
                "Extracts all contained files into the specified directory")
            .def("get_entries", &lotm::big::BigArchive::get_entries, nb::rv_policy::reference_internal,
                "Returns list of indexed file entries");

        nb::class_<lotm::big::BigPacker>(sub, "BigPacker", "Packing engine for BIG4 archives")
            .def_static("pack_from_directory", &lotm::big::BigPacker::pack_from_directory,
                nb::arg("source_dir"), nb::arg("output_file"),
                nb::call_guard<nb::gil_scoped_release>(),
                "Packs a directory tree into a compliant BIG4 archive");
    }

    // Static instance registers this function before NB_MODULE executes
    static BindingRegistrar big_registrar(&register_big_bindings);

} // namespace lotm::python
