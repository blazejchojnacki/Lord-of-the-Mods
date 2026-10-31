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
#include <nanobind/stl/string_view.h>
#include <nanobind/stl/filesystem.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/function.h>

#include "register.hpp"
#include <big/big_archive.hpp>
#include <big/big_packer.hpp>
#include <big/exceptions.hpp>
#include <functional>

namespace nb = nanobind;

namespace lotm::python {

    void register_big_bindings(nb::module_& m) {
        auto sub = m.def_submodule("big", "BIG archive handling");

        // Register custom exceptions
        nb::exception<lotm::big::BigArchiveError> exc_archive(sub, "BigArchiveError");
        nb::exception<lotm::big::BigFormatError>(sub, "BigFormatError", exc_archive);
        nb::exception<lotm::big::BigSecurityError>(sub, "BigSecurityError", exc_archive);

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
                nb::call_guard<nb::gil_scoped_release>(),
                "Open a BIG archive from disk and parses its header index")
            .def("get_entries", &lotm::big::BigArchive::get_entries,
                "Returns list of indexed file entries")
            .def("extract_all", [](const lotm::big::BigArchive& self, const std::filesystem::path& out_dir, std::function<void(std::string_view)> cb) {
            // Wrap the callback to securely reacquire the GIL when invoking Python code
            std::function<void(std::string_view)> safe_cb;
            if (cb) {
                safe_cb = [&cb](std::string_view sv) {
                    nb::gil_scoped_acquire acquire;
                    cb(sv);
                    };
            }

            // Release GIL for the duration of the C++ disk I/O
            nb::gil_scoped_release release;
            self.extract_all(out_dir, safe_cb);
                },
                nb::arg("output_dir"), nb::arg("progress_callback") = nb::none(),
                "Extracts all contained files into the specified directory");

        nb::class_<lotm::big::BigPacker>(sub, "BigPacker", "Packing engine for BIG4 archives")
            .def_static("pack_from_directory", [](const std::filesystem::path& source_dir, const std::filesystem::path& output_file, std::function<void(std::string_view)> cb) {
            // Wrap the callback to securely reacquire the GIL when invoking Python code
            std::function<void(std::string_view)> safe_cb;
            if (cb) {
                safe_cb = [&cb](std::string_view sv) {
                    nb::gil_scoped_acquire acquire;
                    cb(sv);
                    };
            }

            // Release GIL for the duration of the C++ disk I/O
            nb::gil_scoped_release release;
            lotm::big::BigPacker::pack_from_directory(source_dir, output_file, safe_cb);
                },
                nb::arg("source_dir"), nb::arg("output_file"), nb::arg("progress_callback") = nb::none(),
                "Packs a directory tree into a compliant BIG4 archive");
    }

    // Static instance registers this function before NB_MODULE executes
    static BindingRegistrar big_registrar(&register_big_bindings);

} // namespace lotm::python
