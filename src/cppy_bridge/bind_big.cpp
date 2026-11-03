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
#include <nanobind/stl/pair.h>
#include <nanobind/stl/function.h>

#include "register.hpp"
#include <big/big_archive.hpp>
#include <big/big_diff.hpp>
#include <big/big_overlay.hpp>
#include <big/big_packer.hpp>
#include <big/exceptions.hpp>
#include <cstdint>
#include <functional>
#include <string>
#include <utility>
#include <vector>

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
            .def_prop_ro("closed", &lotm::big::BigArchive::is_closed,
                "True if the archive has been closed")
            .def("close", &lotm::big::BigArchive::close,
                "Closes the archive and releases its in-memory index")
            .def("__enter__", [](nb::object self) {
            if (nb::cast<const lotm::big::BigArchive&>(self).is_closed()) {
                throw lotm::big::BigArchiveError("Cannot enter context with a closed archive.");
            }
            return self;
                },
                "Enters the runtime context related to this archive")
            .def("__exit__", [](lotm::big::BigArchive& self, nb::handle, nb::handle, nb::handle) {
            self.close();
                },
                nb::arg("exc_type") = nb::none(),
                nb::arg("exc_val") = nb::none(),
                nb::arg("exc_tb") = nb::none(),
                "Exits the runtime context and closes the archive")
            .def("get_entries", &lotm::big::BigArchive::get_entries,
                nb::arg("filter_pattern") = "",
                "Returns list of indexed file entries")
            .def("read_entry", [](const lotm::big::BigArchive& self, std::string_view entry_name) {
            std::vector<uint8_t> data;
            {
                // Release GIL for the duration of the C++ disk I/O
                nb::gil_scoped_release release;
                data = self.read_entry(entry_name);
            }
            return nb::bytes(reinterpret_cast<const char*>(data.data()), data.size());
                },
                nb::arg("entry"),
                "Reads a single entry by path directly into memory as a buffer-protocol bytes object")
            .def("read_entry", [](const lotm::big::BigArchive& self, const lotm::big::BigEntry& entry) {
            std::vector<uint8_t> data;
            {
                // Release GIL for the duration of the C++ disk I/O
                nb::gil_scoped_release release;
                data = self.read_entry(entry);
            }
            return nb::bytes(reinterpret_cast<const char*>(data.data()), data.size());
                },
                nb::arg("entry"),
                "Reads a single BigEntry record directly into memory as a buffer-protocol bytes object")
            .def("extract_all", [](const lotm::big::BigArchive& self, const std::filesystem::path& out_dir, std::function<void(std::string_view)> cb, std::string_view filter_pattern) {
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
            self.extract_all(out_dir, safe_cb, filter_pattern);
                },
                nb::arg("output_dir"), nb::arg("progress_callback") = nb::none(), nb::arg("filter_pattern") = "",
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
                "Packs a directory tree into a compliant BIG4 archive")
            .def_static("pack_to_memory", [](const std::filesystem::path& source_dir, std::function<void(std::string_view)> cb) {
            // Wrap the callback to securely reacquire the GIL when invoking Python code
            std::function<void(std::string_view)> safe_cb;
            if (cb) {
                safe_cb = [&cb](std::string_view sv) {
                    nb::gil_scoped_acquire acquire;
                    cb(sv);
                    };
            }

            std::vector<uint8_t> data;
            {
                // Release GIL for the duration of the C++ disk I/O and serialization
                nb::gil_scoped_release release;
                data = lotm::big::BigPacker::pack_to_memory(source_dir, safe_cb);
            }
            return nb::bytes(reinterpret_cast<const char*>(data.data()), data.size());
                },
                nb::arg("source"), nb::arg("progress_callback") = nb::none(),
                "Packs a directory tree directly into an in-memory BIG4 archive bytes object")
            .def_static("pack_to_memory", [](const std::vector<std::pair<std::string, nb::bytes>>& files, std::function<void(std::string_view)> cb) {
            // Wrap the callback to securely reacquire the GIL when invoking Python code
            std::function<void(std::string_view)> safe_cb;
            if (cb) {
                safe_cb = [&cb](std::string_view sv) {
                    nb::gil_scoped_acquire acquire;
                    cb(sv);
                    };
            }

            std::vector<std::pair<std::string, std::vector<uint8_t>>> cpp_files;
            cpp_files.reserve(files.size());
            for (const auto& [path, raw_bytes] : files) {
                const auto* ptr = reinterpret_cast<const uint8_t*>(raw_bytes.c_str());
                cpp_files.emplace_back(path, std::vector<uint8_t>(ptr, ptr + raw_bytes.size()));
            }

            std::vector<uint8_t> data;
            {
                // Release GIL for the duration of the C++ sorting and memory serialization
                nb::gil_scoped_release release;
                data = lotm::big::BigPacker::pack_to_memory(cpp_files, safe_cb);
            }
            return nb::bytes(reinterpret_cast<const char*>(data.data()), data.size());
                },
                nb::arg("source"), nb::arg("progress_callback") = nb::none(),
                "Packs a sequence of (path, bytes) pairs directly into an in-memory BIG4 archive bytes object");

        nb::class_<lotm::big::BigDiffResult>(sub, "BigDiffResult", "Comparison result categorizing entries between two BIG4 archives")
            .def_ro("added", &lotm::big::BigDiffResult::added, "Entries present only in the target archive")
            .def_ro("removed", &lotm::big::BigDiffResult::removed, "Entries present only in the base archive")
            .def_ro("modified", &lotm::big::BigDiffResult::modified, "Entries present in both archives with differing content")
            .def_ro("unchanged", &lotm::big::BigDiffResult::unchanged, "Entries present in both archives with identical content")
            .def_prop_ro("has_differences", &lotm::big::BigDiffResult::has_differences, "True if any entries were added, removed, or modified")
            .def("__repr__", [](const lotm::big::BigDiffResult& res) {
            return "<BigDiffResult added=" + std::to_string(res.added.size()) +
                " removed=" + std::to_string(res.removed.size()) +
                " modified=" + std::to_string(res.modified.size()) +
                " unchanged=" + std::to_string(res.unchanged.size()) + ">";
                });

        nb::class_<lotm::big::BigDiff>(sub, "BigDiff", "Comparison and delta patch engine for BIG4 archives")
            .def_static("compare",
                nb::overload_cast<const lotm::big::BigArchive&, const lotm::big::BigArchive&, std::string_view>(&lotm::big::BigDiff::compare),
                nb::arg("base"), nb::arg("target"), nb::arg("filter_pattern") = "",
                nb::call_guard<nb::gil_scoped_release>(),
                "Compares two open BigArchive instances")
            .def_static("compare",
                nb::overload_cast<const std::filesystem::path&, const std::filesystem::path&, std::string_view>(&lotm::big::BigDiff::compare),
                nb::arg("base"), nb::arg("target"), nb::arg("filter_pattern") = "",
                nb::call_guard<nb::gil_scoped_release>(),
                "Compares two BIG4 archive files on disk")
            .def_static("create_patch_to_memory", [](const lotm::big::BigArchive& base, const lotm::big::BigArchive& target, std::string_view filter_pattern, std::function<void(std::string_view)> cb) {
            // Wrap the callback to securely reacquire the GIL when invoking Python code
            std::function<void(std::string_view)> safe_cb;
            if (cb) {
                safe_cb = [&cb](std::string_view sv) {
                    nb::gil_scoped_acquire acquire;
                    cb(sv);
                    };
            }

            std::vector<uint8_t> data;
            {
                // Release GIL for the duration of the C++ diff and packing
                nb::gil_scoped_release release;
                data = lotm::big::BigDiff::create_patch_to_memory(base, target, filter_pattern, safe_cb);
            }
            return nb::bytes(reinterpret_cast<const char*>(data.data()), data.size());
                },
                nb::arg("base"), nb::arg("target"), nb::arg("filter_pattern") = "", nb::arg("progress_callback") = nb::none(),
                "Packs only added and modified entries between two open BigArchive instances into memory")
            .def_static("create_patch_to_memory", [](const std::filesystem::path& base, const std::filesystem::path& target, std::string_view filter_pattern, std::function<void(std::string_view)> cb) {
            // Wrap the callback to securely reacquire the GIL when invoking Python code
            std::function<void(std::string_view)> safe_cb;
            if (cb) {
                safe_cb = [&cb](std::string_view sv) {
                    nb::gil_scoped_acquire acquire;
                    cb(sv);
                    };
            }

            std::vector<uint8_t> data;
            {
                // Release GIL for the duration of the C++ diff and packing
                nb::gil_scoped_release release;
                data = lotm::big::BigDiff::create_patch_to_memory(base, target, filter_pattern, safe_cb);
            }
            return nb::bytes(reinterpret_cast<const char*>(data.data()), data.size());
                },
                nb::arg("base"), nb::arg("target"), nb::arg("filter_pattern") = "", nb::arg("progress_callback") = nb::none(),
                "Packs only added and modified entries between two BIG4 files on disk into memory")
            .def_static("create_patch", [](const lotm::big::BigArchive& base, const lotm::big::BigArchive& target, const std::filesystem::path& output_file, std::string_view filter_pattern, std::function<void(std::string_view)> cb) {
            // Wrap the callback to securely reacquire the GIL when invoking Python code
            std::function<void(std::string_view)> safe_cb;
            if (cb) {
                safe_cb = [&cb](std::string_view sv) {
                    nb::gil_scoped_acquire acquire;
                    cb(sv);
                    };
            }

            // Release GIL for the duration of the C++ diff and disk I/O
            nb::gil_scoped_release release;
            lotm::big::BigDiff::create_patch(base, target, output_file, filter_pattern, safe_cb);
                },
                nb::arg("base"), nb::arg("target"), nb::arg("output_file"), nb::arg("filter_pattern") = "", nb::arg("progress_callback") = nb::none(),
                "Packs only added and modified entries between two open BigArchive instances into a patch file")
            .def_static("create_patch", [](const std::filesystem::path& base, const std::filesystem::path& target, const std::filesystem::path& output_file, std::string_view filter_pattern, std::function<void(std::string_view)> cb) {
            // Wrap the callback to securely reacquire the GIL when invoking Python code
            std::function<void(std::string_view)> safe_cb;
            if (cb) {
                safe_cb = [&cb](std::string_view sv) {
                    nb::gil_scoped_acquire acquire;
                    cb(sv);
                    };
            }

            // Release GIL for the duration of the C++ diff and disk I/O
            nb::gil_scoped_release release;
            lotm::big::BigDiff::create_patch(base, target, output_file, filter_pattern, safe_cb);
                },
                nb::arg("base"), nb::arg("target"), nb::arg("output_file"), nb::arg("filter_pattern") = "", nb::arg("progress_callback") = nb::none(),
                "Packs only added and modified entries between two BIG4 files on disk into a patch file");

        nb::class_<lotm::big::BigOverlayEntry>(sub, "BigOverlayEntry", "Effective entry record resolved across a SAGE archive load order")
            .def_ro("entry", &lotm::big::BigOverlayEntry::entry, "Winning BigEntry metadata record")
            .def_ro("source_archive", &lotm::big::BigOverlayEntry::source_archive, "Path to the archive providing the winning entry")
            .def_ro("override_count", &lotm::big::BigOverlayEntry::override_count, "Number of earlier archives overridden by this entry")
            .def_prop_ro("name", [](const lotm::big::BigOverlayEntry& self) { return self.entry.name; }, "Internal path of the entry")
            .def_prop_ro("size", [](const lotm::big::BigOverlayEntry& self) { return self.entry.size; }, "Size of uncompressed data in bytes")
            .def_prop_ro("offset", [](const lotm::big::BigOverlayEntry& self) { return self.entry.offset; }, "Byte offset within the winning archive")
            .def("__repr__", [](const lotm::big::BigOverlayEntry& self) {
            auto u8 = self.source_archive.filename().u8string();
            std::string filename(reinterpret_cast<const char*>(u8.data()), u8.size());
            return "<BigOverlayEntry name='" + self.entry.name + "' source='" + filename +
                "' overrides=" + std::to_string(self.override_count) + ">";
                });

        nb::class_<lotm::big::BigOverlay>(sub, "BigOverlay", "SAGE engine load-order emulator and virtual archive overlay")
            .def(nb::init<>(), "Initializes an empty SAGE archive overlay")
            .def_static("from_directory", &lotm::big::BigOverlay::from_directory,
                nb::arg("dir_path"),
                nb::call_guard<nb::gil_scoped_release>(),
                "Scans a directory for .big files, sorts them alphabetically, and mounts them")
            .def_static("from_archives", &lotm::big::BigOverlay::from_archives,
                nb::arg("archive_paths"),
                nb::call_guard<nb::gil_scoped_release>(),
                "Mounts a sequence of .big archive files in the specified load order")
            .def("mount", &lotm::big::BigOverlay::mount,
                nb::arg("archive_path"),
                nb::call_guard<nb::gil_scoped_release>(),
                "Mounts a single .big archive on top of the current overlay")
            .def_prop_ro("mounted_archives", &lotm::big::BigOverlay::get_mounted_archives,
                "List of mounted archive paths in load order")
            .def("get_entries", &lotm::big::BigOverlay::get_entries,
                nb::arg("filter_pattern") = "",
                nb::call_guard<nb::gil_scoped_release>(),
                "Returns all effective entries in the overlay sorted alphabetically")
            .def("resolve", &lotm::big::BigOverlay::resolve,
                nb::arg("entry_name"),
                nb::call_guard<nb::gil_scoped_release>(),
                "Resolves the winning BigOverlayEntry for a specific internal path")
            .def("read_entry", [](const lotm::big::BigOverlay& self, std::string_view entry_name) {
            std::vector<uint8_t> data;
            {
                // Release GIL for the duration of the C++ disk I/O
                nb::gil_scoped_release release;
                data = self.read_entry(entry_name);
            }
            return nb::bytes(reinterpret_cast<const char*>(data.data()), data.size());
                },
                nb::arg("entry_name"),
                "Reads the effective winning entry payload directly into memory as bytes");
    }

    // Static instance registers this function before NB_MODULE executes
    static BindingRegistrar big_registrar(&register_big_bindings);

} // namespace lotm::python
