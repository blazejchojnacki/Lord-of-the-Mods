/**
 * @file src/bindings/bind_ini.cpp
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
#include "py_utils.hpp"
#include <core/path_utils.hpp>
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

        using lotm::core::to_utf8;
        using lotm::core::utf8_to_path;

        [[nodiscard]] std::size_t normalize_py_index(Py_ssize_t index, std::size_t size) {
            if (index < 0) {
                index += static_cast<Py_ssize_t>(size);
            }
            if (index < 0 || static_cast<std::size_t>(index) >= size) {
                throw nb::index_error("Index out of range");
            }
            return static_cast<std::size_t>(index);
        }

        template <typename ContainerT, typename ElemT>
        [[nodiscard]] nb::list make_reference_list(nb::handle self, ContainerT& container) {
            nb::list result;
            for (ElemT& elem : container) {
                result.append(nb::cast(elem, nb::rv_policy::reference_internal, self));
            }
            return result;
        }

        [[nodiscard]] nb::list make_block_reference_list(nb::handle self, const std::vector<lotm::ini::ConstructLevel*>& blocks) {
            nb::list result;
            for (lotm::ini::ConstructLevel* ptr : blocks) {
                result.append(nb::cast(*ptr, nb::rv_policy::reference_internal, self));
            }
            return result;
        }

        template <typename ContainerT, typename ItemT, auto StorageMember>
        void bind_sequence_protocol(
            nb::class_<ContainerT>& cls,
            const char* prop_name,
            const char* prop_doc,
            const char* item_arg_name,
            const char* append_doc
        ) {
            cls.def_prop_rw(prop_name,
                [](nb::handle self) {
                    auto& obj = nb::cast<ContainerT&>(self);
                    return make_reference_list<lotm::ini::StableVector<ItemT>, ItemT>(self, obj.*StorageMember);
                },
                [](ContainerT& self, std::vector<ItemT> new_items) {
                    (self.*StorageMember).assign_from(std::move(new_items));
                },
                prop_doc)
                .def("append", [](ContainerT& self, ItemT item) {
                self.append(std::move(item));
                    }, nb::arg(item_arg_name), append_doc)
                .def("__len__", [](const ContainerT& self) { return self.size(); })
                .def("__getitem__", [](ContainerT& self, Py_ssize_t index) -> ItemT& {
                return (self.*StorageMember)[normalize_py_index(index, self.size())];
                    }, nb::arg("index"), nb::rv_policy::reference_internal)
                .def("__setitem__", [](ContainerT& self, Py_ssize_t index, ItemT item) {
                (self.*StorageMember).replace_at(normalize_py_index(index, self.size()), std::move(item));
                    }, nb::arg("index"), nb::arg(item_arg_name))
                .def("__iter__", [](ContainerT& self) {
                return nb::make_iterator<nb::rv_policy::reference_internal>(
                    nb::type<ContainerT>(), "iterator", self.begin(), self.end()
                );
                    }, nb::keep_alive<0, 1>());
        }

        template <typename ContainerT>
        void bind_ast_query_methods(nb::class_<ContainerT>& cls) {
            cls.def("find_block",
                static_cast<lotm::ini::ConstructLevel * (ContainerT::*)(
                    std::string_view,
                    std::optional<std::string_view>,
                    std::optional<std::string_view>,
                    bool
                    )>(&ContainerT::find_block),
                nb::arg("block_class"),
                nb::arg("name") = nb::none(),
                nb::arg("identifier") = nb::none(),
                nb::kw_only(),
                nb::arg("recursive") = false,
                nb::rv_policy::reference_internal,
                "Finds the first ConstructLevel matching block_class, optional name, and optional identifier")
                .def("find_all", [](nb::handle self,
                    std::string_view block_class,
                    std::optional<std::string_view> name,
                    std::optional<std::string_view> identifier,
                    bool recursive) {
                        auto& obj = nb::cast<ContainerT&>(self);
                        return make_block_reference_list(self, obj.find_all(block_class, name, identifier, recursive));
                    },
                    nb::arg("block_class"),
                    nb::arg("name") = nb::none(),
                    nb::arg("identifier") = nb::none(),
                    nb::kw_only(),
                    nb::arg("recursive") = false,
                    "Finds all ConstructLevel blocks matching block_class, optional name, and optional identifier")
                .def("get_value", [](const ContainerT& self, std::string_view key, std::optional<std::string> default_val) {
                auto found = self.get_value(key);
                return found.has_value() ? found : default_val;
                    },
                    nb::arg("key"),
                    nb::arg("default") = nb::none(),
                    "Returns the last matching property value (SAGE override precedence) or default")
                .def("get_all_values", &ContainerT::get_all_values,
                    nb::arg("key"),
                    "Returns all matching property values in document order")
                .def("set_value", &ContainerT::set_value,
                    nb::arg("key"),
                    nb::arg("value"),
                    "Updates the last matching property in-place (preserving formatting and comments) or appends a new statement")
                .def("remove_value", &ContainerT::remove_value,
                    nb::arg("key"),
                    nb::kw_only(),
                    nb::arg("all_occurrences") = false,
                    "Removes the last (or all) matching property statements")
                .def("remove_block", &ContainerT::remove_block,
                    nb::arg("block_class"),
                    nb::arg("name") = nb::none(),
                    nb::arg("identifier") = nb::none(),
                    "Removes the first matching direct child ConstructLevel");
        }

    } // namespace

    void register_ini_bindings(nb::module_& m) {
        auto sub = m.def_submodule("ini", "SAGE engine INI, INC, and STR configuration handling");

        nb::exception<lotm::ini::IniParseError>(sub, "IniParseError", PyExc_ValueError);

        sub.attr("LEVEL_INDENT") = std::string{ lotm::ini::LEVEL_INDENT };
        sub.attr("MAX_INI_DEPTH") = lotm::ini::MAX_INI_DEPTH;
        sub.attr("MAX_INI_FILE_SIZE") = lotm::ini::MAX_INI_FILE_SIZE;
        sub.attr("SAGE_MAX_BLOCK_NAME_LEN") = lotm::ini::SAGE_MAX_BLOCK_NAME_LEN;
        sub.attr("SAGE_MAX_IDENTIFIER_LEN") = lotm::ini::SAGE_MAX_IDENTIFIER_LEN;
        sub.attr("DEFAULT_END") = std::string{ lotm::ini::DEFAULT_END };

        nb::class_<lotm::ini::FormatOptions>(sub, "FormatOptions", "Configurable serialization rules for AST printing and formatting")
            .def("__init__", [](lotm::ini::FormatOptions* t,
                std::string indent,
                bool enforce_equals,
                bool normalize_end_tokens,
                bool normalize_header_spacing,
                bool normalize_statement_equals,
                bool normalize_comments,
                bool coalesce_blank_lines) {
                    new (t) lotm::ini::FormatOptions{
                        std::move(indent),
                        enforce_equals,
                        normalize_end_tokens,
                        normalize_header_spacing,
                        normalize_statement_equals,
                        normalize_comments,
                        coalesce_blank_lines
                    };
                },
                nb::arg("indent") = std::string{ lotm::ini::LEVEL_INDENT },
                nb::arg("enforce_equals") = false,
                nb::arg("normalize_end_tokens") = false,
                nb::arg("normalize_header_spacing") = false,
                nb::arg("normalize_statement_equals") = false,
                nb::arg("normalize_comments") = false,
                nb::arg("coalesce_blank_lines") = false)
            .def_rw("indent", &lotm::ini::FormatOptions::indent, "Indentation string per nesting level")
            .def_rw("enforce_equals", &lotm::ini::FormatOptions::enforce_equals,
                "Emit canonical '=' for delimiters that canonically expect '='")
            .def_rw("normalize_end_tokens", &lotm::ini::FormatOptions::normalize_end_tokens,
                "Normalize End/END/end to 'End' and endscript to 'EndScript'")
            .def_rw("normalize_header_spacing", &lotm::ini::FormatOptions::normalize_header_spacing,
                "Collapse redundant internal whitespace in block and script headers")
            .def_rw("normalize_statement_equals", &lotm::ini::FormatOptions::normalize_statement_equals,
                "Normalize spacing around '=' in key-value statements to 'Key = Value'")
            .def_rw("normalize_comments", &lotm::ini::FormatOptions::normalize_comments,
                "Normalize comment prefixes ('//' or ';') to canonical '; '")
            .def_rw("coalesce_blank_lines", &lotm::ini::FormatOptions::coalesce_blank_lines,
                "Collapse runs of multiple consecutive blank lines into a single blank line")
            .def("__eq__", [](const lotm::ini::FormatOptions& self, const lotm::ini::FormatOptions& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::FormatOptions& self) {
            auto b = [](bool v) { return v ? "True" : "False"; };
            return "<FormatOptions enforce_equals=" + std::string{ b(self.enforce_equals) } +
                " normalize_end_tokens=" + std::string{ b(self.normalize_end_tokens) } +
                " normalize_header_spacing=" + std::string{ b(self.normalize_header_spacing) } +
                " normalize_statement_equals=" + std::string{ b(self.normalize_statement_equals) } +
                " normalize_comments=" + std::string{ b(self.normalize_comments) } +
                " coalesce_blank_lines=" + std::string{ b(self.coalesce_blank_lines) } + ">";
                });

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

        nb::class_<lotm::ini::DefineNode>(sub, "DefineNode", "Represents a #define preprocessor macro directive")
            .def(nb::init<std::string, std::string>(), nb::arg("text") = "", nb::arg("comment") = "")
            .def_rw("text", &lotm::ini::DefineNode::text, "Macro definition text")
            .def_rw("comment", &lotm::ini::DefineNode::comment, "Optional inline comment")
            .def("__eq__", [](const lotm::ini::DefineNode& self, const lotm::ini::DefineNode& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::DefineNode& self) {
            return "<DefineNode text='" + self.text + "'>";
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
            .def("print", [](const lotm::ini::ScriptNode& self,
                int level,
                std::string_view file_type,
                const std::optional<lotm::ini::FormatOptions>& options) {
                    const lotm::ini::FormatOptions opts = options.value_or(lotm::ini::FormatOptions{});
                    nb::gil_scoped_release release;
                    return self.print(level, file_type, opts);
                },
                nb::arg("level") = 0,
                nb::arg("file_type") = ".ini",
                nb::arg("options") = nb::none(),
                "Serializes the script block with consistent indentation")
            .def("__eq__", [](const lotm::ini::ScriptNode& self, const lotm::ini::ScriptNode& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::ScriptNode& self) {
            return "<ScriptNode name='" + self.name + "' identifier='" + self.identifier +
                "' lines=" + std::to_string(self.content.size()) + ">";
                });

        auto cls_construct_level = nb::class_<lotm::ini::ConstructLevel>(
            sub, "ConstructLevel", "Represents an inner block or defined object within a SAGE configuration file"
        );
        cls_construct_level
            .def(nb::init<std::string, std::string, std::string, std::string, std::string, std::string, std::string, std::string, bool>(),
                nb::arg("_class") = "",
                nb::arg("name") = "",
                nb::arg("identifier") = "",
                nb::arg("comment") = "",
                nb::arg("header_comment") = "",
                nb::arg("end_token") = "",
                nb::arg("end_comment") = "",
                nb::arg("canonical_class") = "",
                nb::arg("missing_equals") = false)
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
            .def_rw("canonical_class", &lotm::ini::ConstructLevel::canonical_class, "Canonical delimiter header form")
            .def_rw("missing_equals", &lotm::ini::ConstructLevel::missing_equals, "True if '=' was omitted when expected");

        bind_sequence_protocol<
            lotm::ini::ConstructLevel,
            lotm::ini::AstNode,
            &lotm::ini::ConstructLevel::items
        >(
            cls_construct_level,
            "items",
            "Child AST nodes contained in this block",
            "item",
            "Appends a child AST node to this block"
        );
        bind_ast_query_methods(cls_construct_level);

        cls_construct_level
            .def("print", [](const lotm::ini::ConstructLevel& self,
                int level,
                std::string_view file_type,
                const std::optional<lotm::ini::FormatOptions>& options) {
                    const lotm::ini::FormatOptions opts = options.value_or(lotm::ini::FormatOptions{});
                    nb::gil_scoped_release release;
                    return self.print(level, file_type, opts);
                },
                nb::arg("level") = 0,
                nb::arg("file_type") = ".ini",
                nb::arg("options") = nb::none(),
                "Iteratively serializes this block and all nested children")
            .def("__eq__", [](const lotm::ini::ConstructLevel& self, const lotm::ini::ConstructLevel& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::ConstructLevel& self) {
            return "<ConstructLevel class='" + self._class + "' name='" + self.name +
                "' identifier='" + self.identifier + "' items=" + std::to_string(self.items.size()) + ">";
                });

        auto cls_str_entry = nb::class_<lotm::ini::StrEntry>(
            sub, "StrEntry", "Represents a single localized string entry inside a SAGE .str file"
        );
        cls_str_entry
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
            .def_rw("end_comment", &lotm::ini::StrEntry::end_comment, "Inline comment on the closing line");

        bind_sequence_protocol<
            lotm::ini::StrEntry,
            lotm::ini::StrChildNode,
            &lotm::ini::StrEntry::items
        >(
            cls_str_entry,
            "items",
            "Child comment and statement nodes",
            "item",
            "Appends a child node to this localization entry"
        );

        cls_str_entry
            .def("print", [](const lotm::ini::StrEntry& self,
                const std::optional<lotm::ini::FormatOptions>& options) {
                    const lotm::ini::FormatOptions opts = options.value_or(lotm::ini::FormatOptions{});
                    nb::gil_scoped_release release;
                    return self.print(opts);
                },
                nb::arg("options") = nb::none(),
                "Serializes the localization entry")
            .def("__eq__", [](const lotm::ini::StrEntry& self, const lotm::ini::StrEntry& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::StrEntry& self) {
            return "<StrEntry category='" + self.category + "' identifier='" + self.identifier + "'>";
                });

        auto cls_str_doc = nb::class_<lotm::ini::StrDocument>(
            sub, "StrDocument", "Flat AST representation for SAGE .str localization files"
        );
        cls_str_doc
            .def(nb::init<std::string, std::vector<lotm::ini::StrDocEntry>, std::vector<std::string>>(),
                nb::arg("name") = "",
                nb::arg("entries") = std::vector<lotm::ini::StrDocEntry>{},
                nb::arg("errors") = std::vector<std::string>{})
            .def_rw("name", &lotm::ini::StrDocument::name, "Document file path or identifier")
            .def_rw("errors", &lotm::ini::StrDocument::errors, "Non-strict parsing warnings and errors");

        bind_sequence_protocol<
            lotm::ini::StrDocument,
            lotm::ini::StrDocEntry,
            &lotm::ini::StrDocument::entries
        >(
            cls_str_doc,
            "entries",
            "Top-level localization entries and comments",
            "entry",
            "Appends a top-level entry to the document"
        );

        cls_str_doc
            .def("print", [](const lotm::ini::StrDocument& self,
                const std::optional<lotm::ini::FormatOptions>& options) {
                    const lotm::ini::FormatOptions opts = options.value_or(lotm::ini::FormatOptions{});
                    nb::gil_scoped_release release;
                    return self.print(opts);
                },
                nb::arg("options") = nb::none(),
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
            const std::string path_str = to_utf8(file_path);
            nb::gil_scoped_release release;
            return lotm::ini::StrParser::parse_file(path_str, strict, file_content);
                },
                nb::arg("file_path"),
                nb::arg("strict") = false,
                nb::arg("file_content") = nb::none(),
                "Parses a SAGE .str file from disk or an in-memory string");

        sub.def("parse_str_buffer", [](const std::filesystem::path& file_path, bool strict, nb::object file_buffer) {
            const std::string path_str = to_utf8(file_path);
            ScopedPyBuffer py_buf(file_buffer);
            std::string_view content_view(reinterpret_cast<const char*>(py_buf.view.buf), py_buf.view.len);
            nb::gil_scoped_release release;
            return lotm::ini::StrParser::parse_file(path_str, strict, content_view);
            },
            nb::arg("file_path"), nb::arg("strict"), nb::arg("file_buffer"),
            "Parses a SAGE .str file directly from a Python memoryview or bytes buffer");

        auto cls_construct_file = nb::class_<lotm::ini::ConstructFile>(
            sub, "ConstructFile", "Root AST representation of a parsed SAGE .ini, .inc, or .str document"
        );
        cls_construct_file
            .def("__init__", [](lotm::ini::ConstructFile* t,
                const std::filesystem::path& name,
                bool strict,
                std::optional<std::string> file_content) {
                    std::string name_str = to_utf8(name);
                    nb::gil_scoped_release release;
                    new (t) lotm::ini::ConstructFile(std::move(name_str), strict, std::move(file_content));
                },
                nb::arg("name") = "",
                nb::arg("strict") = false,
                nb::arg("file_content") = nb::none(),
                "Initializes and parses a SAGE .ini, .inc, or .str configuration document")
            .def("__init__", [](lotm::ini::ConstructFile* t,
                const std::filesystem::path& name,
                std::vector<std::string> defines,
                std::vector<std::vector<std::string>> delimiters,
                int start_level,
                bool strict,
                std::optional<std::string> file_content) {
                    std::string name_str = to_utf8(name);
                    nb::gil_scoped_release release;
                    new (t) lotm::ini::ConstructFile();
                    t->name = std::move(name_str);
                    t->defines = std::move(defines);
                    t->delimiters = std::move(delimiters);
                    t->start_level = start_level;
                    t->strict = strict;
                    t->file_content = std::move(file_content);
                    if (!t->name.empty() &&
                        (t->file_content.has_value() || std::filesystem::is_regular_file(utf8_to_path(t->name)))) {
                        t->construct_with_metadata();
                    }
                },
                nb::arg("name"),
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
                    std::string name_str = to_utf8(name);
                    ScopedPyBuffer py_buf(file_buffer);
                    nb::gil_scoped_release release;
                    new (t) lotm::ini::ConstructFile(std::move(name_str), strict, py_buf.as_span());
                },
                nb::arg("name"), nb::arg("strict"), nb::arg("file_buffer"),
                "Initializes and parses a configuration document from a Python memoryview or bytes buffer")
            .def_rw("name", &lotm::ini::ConstructFile::name, "File path or document name")
            .def_rw("defines", &lotm::ini::ConstructFile::defines, "Collected #define macro lines")
            .def_rw("delimiters", &lotm::ini::ConstructFile::delimiters, "Active schema delimiter hierarchy")
            .def_rw("start_level", &lotm::ini::ConstructFile::start_level, "Recognized starting nesting depth")
            .def_rw("strict", &lotm::ini::ConstructFile::strict, "Whether to raise IniParseError on delimiter mismatches")
            .def_rw("file_content", &lotm::ini::ConstructFile::file_content, "Optional in-memory source buffer")
            .def_rw("current_level", &lotm::ini::ConstructFile::current_level, "Current parser nesting level")
            .def_rw("last_comment", &lotm::ini::ConstructFile::last_comment, "Buffered comment awaiting attachment")
            .def_rw("errors", &lotm::ini::ConstructFile::errors, "Accumulated non-strict parsing warnings and errors")
            .def_rw("warnings", &lotm::ini::ConstructFile::warnings, "Accumulated style warnings")
            .def("construct", [](lotm::ini::ConstructFile& self, bool preserve_metadata) {
            nb::gil_scoped_release release;
            self.construct(preserve_metadata);
                },
                nb::arg("preserve_metadata") = false,
                "Parses or re-parses the document into its AST representation")
            .def("construct_with_metadata", [](lotm::ini::ConstructFile& self) {
            nb::gil_scoped_release release;
            self.construct_with_metadata();
                },
                "Parses or re-parses the document while preserving caller-supplied metadata");

        bind_sequence_protocol<
            lotm::ini::ConstructFile,
            lotm::ini::RootItem,
            &lotm::ini::ConstructFile::items
        >(
            cls_construct_file,
            "items",
            "Top-level AST nodes or StrEntry items",
            "item",
            "Appends a top-level AST node or StrEntry to the document"
        );
        bind_ast_query_methods(cls_construct_file);

        cls_construct_file
            .def("print", [](const lotm::ini::ConstructFile& self,
                const std::optional<lotm::ini::FormatOptions>& options) {
                    const lotm::ini::FormatOptions opts = options.value_or(lotm::ini::FormatOptions{});
                    nb::gil_scoped_release release;
                    return self.print(opts);
                },
                nb::arg("options") = nb::none(),
                "Iteratively serializes the document back into formatted configuration text")
            .def("__eq__", [](const lotm::ini::ConstructFile& self, const lotm::ini::ConstructFile& other) {
            return self == other;
                })
            .def("__repr__", [](const lotm::ini::ConstructFile& self) {
            return "<ConstructFile name='" + self.name + "' items=" + std::to_string(self.items.size()) +
                " errors=" + std::to_string(self.errors.size()) + ">";
                });

        sub.def("recognize_structure", [](const std::filesystem::path& file_path, std::optional<std::string_view> file_content) {
            const std::string path_str = to_utf8(file_path);
            nb::gil_scoped_release release;
            return lotm::ini::recognize_structure(path_str, file_content);
            },
            nb::arg("file_path"),
            nb::arg("file_content") = nb::none(),
            "Recognizes the delimiter hierarchy and starting nesting depth of a SAGE .ini, .inc, or .str file");

        sub.def("recognize_structure_buffer", [](const std::filesystem::path& file_path, nb::object file_buffer) {
            const std::string path_str = to_utf8(file_path);
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
            const std::string path_str = to_utf8(full_path);
            nb::gil_scoped_release release;
            return lotm::ini::load_file(path_str);
            },
            nb::arg("full_path"),
            "Loads and normalizes a structured (.ini, .inc, .str) or raw (.txt) file");

        sub.def("scan_file_for_errors", [](const std::filesystem::path& file_path) {
            const std::string path_str = to_utf8(file_path);
            nb::gil_scoped_release release;
            return lotm::ini::scan_file_for_errors(path_str);
            },
            nb::arg("file_path"),
            "Parses a file in non-strict mode and returns any delimiter or level mismatch errors");
    }

    static BindingRegistrar ini_registrar(&register_ini_bindings);

} // namespace lotm::python
