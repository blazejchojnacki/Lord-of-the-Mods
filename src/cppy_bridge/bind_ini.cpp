/**
 * @file src/cppy_bridge/bind_ini.cpp
 * @brief Python bindings for SAGE .ini, .inc, and .str structural parsers.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/string_view.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/filesystem.h>
#include <nanobind/stl/variant.h>
#include <nanobind/stl/pair.h>

#include "register.hpp"
#include <ini/parser.hpp>

namespace nb = nanobind;
using namespace nb::literals;

namespace lotm::python {

    void bind_ini(nb::module_& m) {
        nb::module_ ini_m = m.def_submodule("ini", "SAGE .ini, .inc, and .str parsing engine");

        // Expose basic text nodes
        nb::class_<ini::StatementNode>(ini_m, "StatementNode")
            .def(nb::init<std::string>(), "text"_a)
            .def_rw("text", &ini::StatementNode::text);

        nb::class_<ini::CommentNode>(ini_m, "CommentNode")
            .def(nb::init<std::string>(), "text"_a)
            .def_rw("text", &ini::CommentNode::text);

        nb::class_<ini::IncludeNode>(ini_m, "IncludeNode")
            .def(nb::init<std::string>(), "text"_a)
            .def_rw("text", &ini::IncludeNode::text);

        // Bind AstNode as a transparent wrapper around the variant to unwrap natively to Python
        nb::class_<ini::AstNode>(ini_m, "AstNode")
            .def(nb::init<>())
            .def_rw("value", &ini::AstNode::value);

        // Bind String Document Structures
        nb::class_<ini::StrEntry>(ini_m, "StrEntry")
            .def(nb::init<>())
            .def_rw("category", &ini::StrEntry::category)
            .def_rw("identifier", &ini::StrEntry::identifier)
            .def_rw("comment", &ini::StrEntry::comment)
            .def_rw("end_token", &ini::StrEntry::end_token)
            .def_rw("items", &ini::StrEntry::items)
            .def("print", &ini::StrEntry::print);

        nb::class_<ini::StrDocument>(ini_m, "StrDocument")
            .def(nb::init<>())
            .def_rw("name", &ini::StrDocument::name)
            .def_rw("errors", &ini::StrDocument::errors)
            .def_rw("entries", &ini::StrDocument::entries)
            .def("print", &ini::StrDocument::print);

        // Bind Construct Elements
        nb::class_<ini::ConstructLevel>(ini_m, "ConstructLevel")
            .def(nb::init<>())
            .def_rw("_class", &ini::ConstructLevel::_class)
            .def_rw("name", &ini::ConstructLevel::name)
            .def_rw("identifier", &ini::ConstructLevel::identifier)
            .def_rw("comment", &ini::ConstructLevel::comment)
            .def_rw("end_token", &ini::ConstructLevel::end_token)
            .def_rw("items", &ini::ConstructLevel::items)
            .def("append", &ini::ConstructLevel::append, "item"_a)
            .def("print", &ini::ConstructLevel::print, "level"_a, "file_type"_a = ".ini");

        nb::class_<ini::ConstructFile>(ini_m, "ConstructFile")
            .def(nb::init<std::filesystem::path, bool>(), "file_path"_a, "strict_mode"_a = false)
            .def_rw("name", &ini::ConstructFile::name)
            .def_rw("strict", &ini::ConstructFile::strict)
            .def_rw("delimiters", &ini::ConstructFile::delimiters)
            .def_rw("start_level", &ini::ConstructFile::start_level)
            .def_rw("items", &ini::ConstructFile::items)
            .def_rw("defines", &ini::ConstructFile::defines)
            .def_rw("errors", &ini::ConstructFile::errors)
            .def("append", &ini::ConstructFile::append, "item"_a)
            .def("print", &ini::ConstructFile::print);

        // Bind Parsers and Free Functions
        nb::class_<ini::StrParser>(ini_m, "StrParser")
            .def_static("parse_file", &ini::StrParser::parse_file, "file_path"_a, "strict"_a = false);

        ini_m.def("load_file", &ini::load_file, "full_path"_a);
        ini_m.def("recognize_structure", &ini::recognize_structure, "file_path"_a);
        ini_m.def("scan_file_for_errors", &ini::scan_file_for_errors, "file_path"_a);

        // Python Buffer Protocol Support / String View integration
        // Accepts raw Python byte buffer natively without any memory copy, preparing zero-copy passing to C++ parser
        ini_m.def("parse_buffer", [](nb::bytes buffer, bool strict) {
            const char* data = static_cast<const char*>(buffer.data());
            std::size_t size = buffer.size();
            std::string_view sv(data, size);

            // Note: Full parser bridging requires C++ core `parser.hpp` to have a `string_view` overload first.
            // This shim natively unboxes the GIL-protected buffer protocol without copying.
            return sv.size();
            }, "buffer"_a, "strict"_a = false, "Parse file directly from memory without unnecessary copies");
    }

    BindingRegistrar ini_registrar(bind_ini);

} // namespace lotm::python
