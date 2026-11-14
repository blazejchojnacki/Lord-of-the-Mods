/**
 * @file src/cppy_bridge/bind_ini.cpp
 * @brief Binding .INI, .INC, and .STR configuration parser features
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <nanobind/nanobind.h>
#include <nanobind/make_iterator.h>
#include <nanobind/stl/filesystem.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/pair.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/string_view.h>
#include <nanobind/stl/variant.h>
#include <nanobind/stl/vector.h>

#include "register.hpp"
#include <ini/lexer.hpp>
#include <ini/parser.hpp>
#include <ini/schema.hpp>
#include "ini/ast.hpp"

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace nb = nanobind;

namespace lotm::python {

    namespace {

        [[nodiscard]] std::string path_to_utf8(const std::filesystem::path& p) {
            const auto u8 = p.u8string();
            return std::string(reinterpret_cast<const char*>(u8.data()), u8.size());
        }

        [[nodiscard]] std::size_t normalize_py_index(Py_ssize_t index, std::size_t size) {
            if (index < 0) {
                index += static_cast<Py_ssize_t>(size);
            }
            if (index < 0 || static_cast<std::size_t>(index) >= size) {
                throw nb::index_error("Index out of range");
            }
            return static_cast<std::size_t>(index);
        }

        struct ScopedPyBuffer {
            Py_buffer view{};
            bool valid{ false };

            explicit ScopedPyBuffer(nb::handle obj) {
                if (PyObject_GetBuffer(obj.ptr(), &view, PyBUF_SIMPLE) != 0) {
                    throw nb::python_error();
                }
                valid = true;
            }

            ScopedPyBuffer(const ScopedPyBuffer&) = delete;
            ScopedPyBuffer& operator=(const ScopedPyBuffer&) = delete;

            ~ScopedPyBuffer() {
                if (valid) {
                    PyBuffer_Release(&view);
                }
            }

            [[nodiscard]] std::span<const uint8_t> as_span() const noexcept {
                return std::span<const uint8_t>(
                    static_cast<const uint8_t*>(view.buf),
                    static_cast<std::size_t>(view.len)
                );
            }
        };

    } // namespace

    void register_ini_bindings(nb::module_& m) {
        auto sub = m.def_submodule("ini", "SAGE engine INI, INC, and STR configuration handling");

        nb::exception<lotm::ini::IniParseError>(sub, "IniParseError", PyExc_ValueError);

        sub.attr("LEVEL_INDENT") = std::string{ lotm::ini::LEVEL_INDENT };
        sub.attr("MAX_INI_DEPTH") = lotm::ini::MAX_INI_DEPTH;
        sub.attr("MAX_INI_FILE_SIZE") = lotm::ini::MAX_INI_FILE_SIZE;
        sub.attr("SAGE_MAX_BLOCK_NAME_LEN") = lotm::ini::SAGE_MAX_BLOCK_NAME_LEN;
        sub.attr("SAGE_MAX_IDENTIFIER_LEN") = lotm::ini::SAGE_MAX_IDENTIFIER_LEN;

        nb::list ini_ends_list;
        for (const auto kw : lotm::ini::INI_ENDS) {
            ini_ends_list.append(kw);
        }
        sub.attr("INI_ENDS") = nb::tuple(ini_ends_list);

        nb::class_<lotm::ini::CommentNode>(sub, "CommentNode", "Represents a standalone or block-internal comment")
            .def(nb::init<std::string>(), nb::arg("text") = "")
            .def_rw("text", &lotm::ini::CommentNode::text, "Raw comment text")
            .def("__eq__", [](const lotm::ini::CommentNode& self, const lotm::ini::CommentNode& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::CommentNode& self) {
            return "<CommentNode text='" + self.text + "'>";
                });

        nb::class_<lotm::ini::StatementNode>(sub, "StatementNode", "Represents a standard property assignment or value line")
            .def(nb::init<std::string, std::string>(), nb::arg("text") = "", nb::arg("comment") = "")
            .def_rw("text", &lotm::ini::StatementNode::text, "Code statement text")
            .def_rw("comment", &lotm::ini::StatementNode::comment, "Optional inline comment")
            .def("__eq__", [](const lotm::ini::StatementNode& self, const lotm::ini::StatementNode& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::StatementNode& self) {
            return "<StatementNode text='" + self.text + "'>";
                });

        nb::class_<lotm::ini::IncludeNode>(sub, "IncludeNode", "Represents a #include preprocessor directive")
            .def(nb::init<std::string, std::string>(), nb::arg("raw_path") = "", nb::arg("comment") = "")
            .def_rw("raw_path", &lotm::ini::IncludeNode::raw_path, "Raw path token as written in the file")
            .def_rw("comment", &lotm::ini::IncludeNode::comment, "Optional inline comment")
            .def_prop_ro("clean_path", &lotm::ini::IncludeNode::clean_path,
                "Normalized path with surrounding quotes stripped and forward slashes")
            .def("__eq__", [](const lotm::ini::IncludeNode& self, const lotm::ini::IncludeNode& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::IncludeNode& self) {
            return "<IncludeNode raw_path='" + self.raw_path + "'>";
                });

        nb::class_<lotm::ini::ScriptNode>(sub, "ScriptNode", "Represents an opaque embedded script block (BeginScript ... EndScript)")
            .def(nb::init<std::string, std::string, std::string, std::string, std::string, std::string, std::vector<std::string>>(),
                nb::arg("name") = "BeginScript",
                nb::arg("identifier") = "",
                nb::arg("comment") = "",
                nb::arg("header_comment") = "",
                nb::arg("end_token") = "EndScript",
                nb::arg("end_comment") = "",
                nb::arg("content") = std::vector<std::string>{})
            .def_prop_rw("name",
                [](const lotm::ini::ScriptNode& self) { return self.name; },
                [](lotm::ini::ScriptNode& self, std::string val) {
                    lotm::ini::validate_sage_bounds(val, self.identifier);
                    self.name = std::move(val);
                },
                "Opening script keyword")
            .def_prop_rw("identifier",
                [](const lotm::ini::ScriptNode& self) { return self.identifier; },
                [](lotm::ini::ScriptNode& self, std::string val) {
                    lotm::ini::validate_sage_bounds(self.name, val);
                    self.identifier = std::move(val);
                },
                "Optional script identifier")
            .def_rw("comment", &lotm::ini::ScriptNode::comment, "Leading comment block")
            .def_rw("header_comment", &lotm::ini::ScriptNode::header_comment, "Inline comment on the opening line")
            .def_rw("end_token", &lotm::ini::ScriptNode::end_token, "Closing script keyword")
            .def_rw("end_comment", &lotm::ini::ScriptNode::end_comment, "Inline comment on the closing line")
            .def_rw("content", &lotm::ini::ScriptNode::content, "Raw script body lines")
            .def("print", &lotm::ini::ScriptNode::print,
                nb::arg("level") = 0,
                nb::arg("file_type") = ".ini",
                nb::call_guard<nb::gil_scoped_release>(),
                "Serializes the script block with consistent indentation")
            .def("__eq__", [](const lotm::ini::ScriptNode& self, const lotm::ini::ScriptNode& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::ScriptNode& self) {
            return "<ScriptNode name='" + self.name + "' identifier='" + self.identifier +
                "' lines=" + std::to_string(self.content.size()) + ">";
                });

        nb::class_<lotm::ini::ConstructLevel>(sub, "ConstructLevel", "Represents an inner block or defined object within a SAGE configuration file")
            .def(nb::init<std::string, std::string, std::string, std::string, std::string, std::string, std::string>(),
                nb::arg("_class") = "",
                nb::arg("name") = "",
                nb::arg("identifier") = "",
                nb::arg("comment") = "",
                nb::arg("header_comment") = "",
                nb::arg("end_token") = "",
                nb::arg("end_comment") = "")
            .def_prop_rw("_class",
                [](const lotm::ini::ConstructLevel& self) { return self._class; },
                [](lotm::ini::ConstructLevel& self, std::string val) {
                    lotm::ini::validate_sage_bounds(self.name, self.identifier, val);
                    self._class = std::move(val);
                },
                "Delimiter class keyword")
            .def_prop_rw("name",
                [](const lotm::ini::ConstructLevel& self) { return self.name; },
                [](lotm::ini::ConstructLevel& self, std::string val) {
                    lotm::ini::validate_sage_bounds(val, self.identifier, self._class);
                    self.name = std::move(val);
                },
                "Block name or type")
            .def_prop_rw("identifier",
                [](const lotm::ini::ConstructLevel& self) { return self.identifier; },
                [](lotm::ini::ConstructLevel& self, std::string val) {
                    lotm::ini::validate_sage_bounds(self.name, val, self._class);
                    self.identifier = std::move(val);
                },
                "Optional module tag or sub-identifier")
            .def_rw("comment", &lotm::ini::ConstructLevel::comment, "Leading comment block")
            .def_rw("header_comment", &lotm::ini::ConstructLevel::header_comment, "Inline comment on the header line")
            .def_rw("end_token", &lotm::ini::ConstructLevel::end_token, "Closing keyword (End, END, end)")
            .def_rw("end_comment", &lotm::ini::ConstructLevel::end_comment, "Inline comment on the closing line")
            .def_rw("items", &lotm::ini::ConstructLevel::items, "Child AST nodes contained in this block")
            .def("append", &lotm::ini::ConstructLevel::append, nb::arg("item"), "Appends a child AST node to this block")
            .def("__len__", &lotm::ini::ConstructLevel::size)
            .def("__getitem__", [](lotm::ini::ConstructLevel& self, Py_ssize_t index) -> lotm::ini::AstNode& {
            return self.items[normalize_py_index(index, self.size())];
                }, nb::arg("index"), nb::rv_policy::reference_internal)
            .def("__setitem__", [](lotm::ini::ConstructLevel& self, Py_ssize_t index, lotm::ini::AstNode item) {
            self.items[normalize_py_index(index, self.size())] = std::move(item);
                }, nb::arg("index"), nb::arg("item"))
            .def("__iter__", [](lotm::ini::ConstructLevel& self) {
            return nb::make_iterator<nb::rv_policy::reference_internal>(
                nb::type<lotm::ini::ConstructLevel>(), "iterator", self.begin(), self.end()
            );
                }, nb::keep_alive<0, 1>())
            .def("print", &lotm::ini::ConstructLevel::print,
                nb::arg("level") = 0,
                nb::arg("file_type") = ".ini",
                nb::call_guard<nb::gil_scoped_release>(),
                "Iteratively serializes this block and all nested children")
            .def("__eq__", [](const lotm::ini::ConstructLevel& self, const lotm::ini::ConstructLevel& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::ConstructLevel& self) {
            return "<ConstructLevel class='" + self._class + "' name='" + self.name +
                "' identifier='" + self.identifier + "' items=" + std::to_string(self.items.size()) + ">";
                });

        nb::class_<lotm::ini::StrEntry>(sub, "StrEntry", "Represents a single localized string entry inside a SAGE .str file")
            .def(nb::init<std::string, std::string, std::string, std::string, std::string, std::string, std::vector<lotm::ini::StrChildNode>>(),
                nb::arg("category"),
                nb::arg("identifier"),
                nb::arg("comment") = "",
                nb::arg("header_comment") = "",
                nb::arg("end_token") = "End",
                nb::arg("end_comment") = "",
                nb::arg("items") = std::vector<lotm::ini::StrChildNode>{})
            .def_prop_rw("category",
                [](const lotm::ini::StrEntry& self) { return self.category; },
                [](lotm::ini::StrEntry& self, std::string val) {
                    lotm::ini::validate_sage_bounds(val, self.identifier);
                    self.category = std::move(val);
                },
                "Localization string category prefix")
            .def_prop_rw("identifier",
                [](const lotm::ini::StrEntry& self) { return self.identifier; },
                [](lotm::ini::StrEntry& self, std::string val) {
                    lotm::ini::validate_sage_bounds(self.category, val);
                    self.identifier = std::move(val);
                },
                "Localization key identifier")
            .def_rw("comment", &lotm::ini::StrEntry::comment, "Leading comment block")
            .def_rw("header_comment", &lotm::ini::StrEntry::header_comment, "Inline comment on the header line")
            .def_rw("end_token", &lotm::ini::StrEntry::end_token, "Closing keyword")
            .def_rw("end_comment", &lotm::ini::StrEntry::end_comment, "Inline comment on the closing line")
            .def_rw("items", &lotm::ini::StrEntry::items, "Child comment and statement nodes")
            .def("append", &lotm::ini::StrEntry::append, nb::arg("item"), "Appends a child node to this localization entry")
            .def("__len__", &lotm::ini::StrEntry::size)
            .def("__getitem__", [](lotm::ini::StrEntry& self, Py_ssize_t index) -> lotm::ini::StrChildNode& {
            return self.items[normalize_py_index(index, self.size())];
                }, nb::arg("index"), nb::rv_policy::reference_internal)
            .def("__setitem__", [](lotm::ini::StrEntry& self, Py_ssize_t index, lotm::ini::StrChildNode item) {
            self.items[normalize_py_index(index, self.size())] = std::move(item);
                }, nb::arg("index"), nb::arg("item"))
            .def("__iter__", [](lotm::ini::StrEntry& self) {
            return nb::make_iterator<nb::rv_policy::reference_internal>(
                nb::type<lotm::ini::StrEntry>(), "iterator", self.begin(), self.end()
            );
                }, nb::keep_alive<0, 1>())
            .def("print", &lotm::ini::StrEntry::print,
                nb::call_guard<nb::gil_scoped_release>(),
                "Serializes the localization entry")
            .def("__eq__", [](const lotm::ini::StrEntry& self, const lotm::ini::StrEntry& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::StrEntry& self) {
            return "<StrEntry category='" + self.category + "' identifier='" + self.identifier + "'>";
                });

        nb::class_<lotm::ini::StrDocument>(sub, "StrDocument", "Flat AST representation for SAGE .str localization files")
            .def(nb::init<std::string, std::vector<lotm::ini::StrDocEntry>, std::vector<std::string>>(),
                nb::arg("name") = "",
                nb::arg("entries") = std::vector<lotm::ini::StrDocEntry>{},
                nb::arg("errors") = std::vector<std::string>{})
            .def_rw("name", &lotm::ini::StrDocument::name, "Document file path or identifier")
            .def_rw("entries", &lotm::ini::StrDocument::entries, "Top-level localization entries and comments")
            .def_rw("errors", &lotm::ini::StrDocument::errors, "Non-strict parsing warnings and errors")
            .def("append", &lotm::ini::StrDocument::append, nb::arg("entry"), "Appends a top-level entry to the document")
            .def("__len__", &lotm::ini::StrDocument::size)
            .def("__getitem__", [](lotm::ini::StrDocument& self, Py_ssize_t index) -> lotm::ini::StrDocEntry& {
            return self.entries[normalize_py_index(index, self.size())];
                }, nb::arg("index"), nb::rv_policy::reference_internal)
            .def("__setitem__", [](lotm::ini::StrDocument& self, Py_ssize_t index, lotm::ini::StrDocEntry entry) {
            self.entries[normalize_py_index(index, self.size())] = std::move(entry);
                }, nb::arg("index"), nb::arg("entry"))
            .def("__iter__", [](lotm::ini::StrDocument& self) {
            return nb::make_iterator<nb::rv_policy::reference_internal>(
                nb::type<lotm::ini::StrDocument>(), "iterator", self.begin(), self.end()
            );
                }, nb::keep_alive<0, 1>())
            .def("print", &lotm::ini::StrDocument::print,
                nb::call_guard<nb::gil_scoped_release>(),
                "Serializes the entire .str document")
            .def("__eq__", [](const lotm::ini::StrDocument& self, const lotm::ini::StrDocument& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::StrDocument& self) {
            return "<StrDocument name='" + self.name + "' entries=" + std::to_string(self.entries.size()) +
                " errors=" + std::to_string(self.errors.size()) + ">";
                });

        nb::class_<lotm::ini::StrParser>(sub, "StrParser", "Dedicated single-level parser for SAGE .str localization files")
            .def_static("parse_file", [](const std::filesystem::path& file_path, bool strict, std::optional<std::string_view> file_content) {
            const std::string path_str = path_to_utf8(file_path);
            nb::gil_scoped_release release;
            return lotm::ini::StrParser::parse_file(path_str, strict, file_content);
                },
                nb::arg("file_path"),
                nb::arg("strict") = false,
                nb::arg("file_content") = nb::none(),
                "Parses a SAGE .str file from disk or an in-memory string");

        sub.def("parse_str_buffer", [](const std::filesystem::path& file_path, bool strict, nb::object file_buffer) {
            const std::string path_str = path_to_utf8(file_path);
            ScopedPyBuffer py_buf(file_buffer);
            std::string_view content_view(reinterpret_cast<const char*>(py_buf.view.buf), py_buf.view.len);
            nb::gil_scoped_release release;
            return lotm::ini::StrParser::parse_file(path_str, strict, content_view);
            },
            nb::arg("file_path"), nb::arg("strict"), nb::arg("file_buffer"),
            "Parses a SAGE .str file directly from a Python memoryview or bytes buffer");

        nb::class_<lotm::ini::ConstructFile>(sub, "ConstructFile", "Root AST representation of a parsed SAGE .ini, .inc, or .str document")
            .def("__init__", [](lotm::ini::ConstructFile* t,
                const std::filesystem::path& name,
                bool strict,
                std::optional<std::string> file_content) {
                    std::string name_str = path_to_utf8(name);
                    nb::gil_scoped_release release;
                    new (t) lotm::ini::ConstructFile(std::move(name_str), strict, std::move(file_content));
                },
                nb::arg("name") = "",
                nb::arg("strict") = false,
                nb::arg("file_content") = nb::none(),
                "Initializes and parses a SAGE .ini, .inc, or .str configuration document")
            .def("__init__", [](lotm::ini::ConstructFile* t,
                const std::filesystem::path& name,
                std::string comment,
                std::vector<std::string> defines,
                std::vector<std::vector<std::string>> delimiters,
                int start_level,
                bool strict,
                std::optional<std::string> file_content) {
                    std::string name_str = path_to_utf8(name);
                    nb::gil_scoped_release release;
                    new (t) lotm::ini::ConstructFile();
                    t->name = std::move(name_str);
                    t->comment = std::move(comment);
                    t->defines = std::move(defines);
                    t->delimiters = std::move(delimiters);
                    t->start_level = start_level;
                    t->strict = strict;
                    t->file_content = std::move(file_content);
                    if (!t->name.empty()) {
                        t->construct();
                    }
                },
                nb::arg("name"),
                nb::arg("comment"),
                nb::arg("defines") = std::vector<std::string>{},
                nb::arg("delimiters") = std::vector<std::vector<std::string>>{},
                nb::arg("start_level") = 0,
                nb::arg("strict") = false,
                nb::arg("file_content") = nb::none(),
                "Initializes a ConstructFile with explicit metadata attributes")
            .def("__init__", [](lotm::ini::ConstructFile* t,
                const std::filesystem::path& name,
                bool strict,
                nb::object file_buffer) {
                    std::string name_str = path_to_utf8(name);
                    ScopedPyBuffer py_buf(file_buffer);
                    nb::gil_scoped_release release;
                    new (t) lotm::ini::ConstructFile(std::move(name_str), strict, py_buf.as_span());
                },
                nb::arg("name"), nb::arg("strict"), nb::arg("file_buffer"),
                "Initializes and parses a configuration document from a Python memoryview or bytes buffer")
            .def_rw("name", &lotm::ini::ConstructFile::name, "File path or document name")
            .def_rw("comment", &lotm::ini::ConstructFile::comment, "Document-level comment")
            .def_rw("defines", &lotm::ini::ConstructFile::defines, "Collected #define macro lines")
            .def_rw("delimiters", &lotm::ini::ConstructFile::delimiters, "Active schema delimiter hierarchy")
            .def_rw("start_level", &lotm::ini::ConstructFile::start_level, "Recognized starting nesting depth")
            .def_rw("strict", &lotm::ini::ConstructFile::strict, "Whether to raise IniParseError on delimiter mismatches")
            .def_rw("file_content", &lotm::ini::ConstructFile::file_content, "Optional in-memory source buffer")
            .def_rw("items", &lotm::ini::ConstructFile::items, "Top-level AST nodes or StrEntry items")
            .def_rw("current_level", &lotm::ini::ConstructFile::current_level, "Current parser nesting level")
            .def_rw("last_comment", &lotm::ini::ConstructFile::last_comment, "Buffered comment awaiting attachment")
            .def_rw("errors", &lotm::ini::ConstructFile::errors, "Accumulated non-strict parsing warnings and errors")
            .def("construct", &lotm::ini::ConstructFile::construct,
                nb::call_guard<nb::gil_scoped_release>(),
                "Parses or re-parses the document into its AST representation")
            .def("append", static_cast<void (lotm::ini::ConstructFile::*)(lotm::ini::RootItem)>(&lotm::ini::ConstructFile::append),
                nb::arg("item"),
                "Appends a top-level AST node or StrEntry to the document")
            .def("__len__", &lotm::ini::ConstructFile::size)
            .def("__getitem__", [](lotm::ini::ConstructFile& self, Py_ssize_t index) -> lotm::ini::RootItem& {
            return self.items[normalize_py_index(index, self.size())];
                }, nb::arg("index"), nb::rv_policy::reference_internal)
            .def("__setitem__", [](lotm::ini::ConstructFile& self, Py_ssize_t index, lotm::ini::RootItem item) {
            self.items[normalize_py_index(index, self.size())] = std::move(item);
                }, nb::arg("index"), nb::arg("item"))
            .def("__iter__", [](lotm::ini::ConstructFile& self) {
            return nb::make_iterator<nb::rv_policy::reference_internal>(
                nb::type<lotm::ini::ConstructFile>(), "iterator", self.begin(), self.end()
            );
                }, nb::keep_alive<0, 1>())
            .def("print", &lotm::ini::ConstructFile::print,
                nb::call_guard<nb::gil_scoped_release>(),
                "Iteratively serializes the document back into formatted configuration text")
            .def("__eq__", [](const lotm::ini::ConstructFile& self, const lotm::ini::ConstructFile& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::ConstructFile& self) {
            return "<ConstructFile name='" + self.name + "' items=" + std::to_string(self.items.size()) +
                " errors=" + std::to_string(self.errors.size()) + ">";
                });

        sub.def("recognize_structure", [](const std::filesystem::path& file_path, std::optional<std::string_view> file_content) {
            const std::string path_str = path_to_utf8(file_path);
            nb::gil_scoped_release release;
            return lotm::ini::recognize_structure(path_str, file_content);
            },
            nb::arg("file_path"),
            nb::arg("file_content") = nb::none(),
            "Recognizes the delimiter hierarchy and starting nesting depth of a SAGE .ini, .inc, or .str file");

        sub.def("recognize_structure_buffer", [](const std::filesystem::path& file_path, nb::object file_buffer) {
            const std::string path_str = path_to_utf8(file_path);
            ScopedPyBuffer py_buf(file_buffer);
            std::string_view content_view(reinterpret_cast<const char*>(py_buf.view.buf), py_buf.view.len);
            nb::gil_scoped_release release;
            return lotm::ini::recognize_structure(path_str, content_view);
            },
            nb::arg("file_path"), nb::arg("file_buffer"),
            "Recognizes the delimiter hierarchy and starting nesting depth from a Python memoryview or bytes buffer");

        sub.def("validate_include", &lotm::ini::validate_include,
            nb::arg("node"),
            nb::arg("current_file"),
            nb::arg("virtual_root"),
            nb::call_guard<nb::gil_scoped_release>(),
            "Validates and resolves a #include directive path strictly within the virtual root jail");

        sub.def("load_file", [](const std::filesystem::path& full_path) {
            const std::string path_str = path_to_utf8(full_path);
            nb::gil_scoped_release release;
            return lotm::ini::load_file(path_str);
            },
            nb::arg("full_path"),
            "Loads and normalizes a structured (.ini, .inc, .str) or raw (.txt) file");

        sub.def("scan_file_for_errors", [](const std::filesystem::path& file_path) {
            const std::string path_str = path_to_utf8(file_path);
            nb::gil_scoped_release release;
            return lotm::ini::scan_file_for_errors(path_str);
            },
            nb::arg("file_path"),
            "Parses a file in non-strict mode and returns any delimiter or level mismatch errors");
    }

    static BindingRegistrar ini_registrar(&register_ini_bindings);

} // namespace lotm::python
