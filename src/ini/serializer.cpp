/**
 * @file src/ini/serializer.cpp
 * @brief Implementation of iterative AST serialization and node printing methods.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "parser_utils.hpp"
#include "ini/parser.hpp"

#include <algorithm>
#include <type_traits>

namespace lotm::ini {

    namespace {

        void append_indent(std::string& out, int level) {
            for (int i = 0; i < level; ++i) {
                out.append(LEVEL_INDENT);
            }
        }

        void append_indented_text(std::string& out, std::string_view text, int level) {
            const int safe_level = std::max(0, level);
            if (text.find('\n') != std::string_view::npos) {
                std::size_t pos = 0;
                while (pos <= text.size()) {
                    const std::size_t next_nl = text.find('\n', pos);
                    const std::string_view slice = (next_nl == std::string_view::npos)
                        ? text.substr(pos)
                        : text.substr(pos, next_nl - pos);

                    append_indent(out, safe_level);
                    out.append(detail::lstrip_view(slice));
                    out.push_back('\n');

                    if (next_nl == std::string_view::npos) {
                        break;
                    }
                    pos = next_nl + 1;
                }
                return;
            }

            append_indent(out, safe_level);
            out.append(text);
            out.push_back('\n');
        }

    } // namespace

    std::string serialize_iterative(
        std::span<const SerializableNodeRef> items,
        int start_level,
        std::string_view file_type
    ) {
        std::string output;
        const std::string_view sep = detail::ends_with_ci(file_type, ".str") ? ":" : " ";

        std::vector<SerializationFrame> stack;
        stack.reserve(items.size() * 2 + 8);

        for (auto it = items.rbegin(); it != items.rend(); ++it) {
            stack.push_back(SerializationFrame{ *it, start_level, false });
        }

        while (!stack.empty()) {
            const SerializationFrame frame = stack.back();
            stack.pop_back();

            if (frame.is_closing) {
                std::visit([&](const auto* node_ptr) {
                    using NodeT = std::decay_t<decltype(*node_ptr)>;
                    if constexpr (std::is_same_v<NodeT, ConstructLevel>) {
                        if (!node_ptr->end_token.empty()) {
                            const std::string end_line = detail::combine_text_and_comment(
                                node_ptr->end_token, node_ptr->end_comment
                            );
                            append_indent(output, std::max(0, frame.level));
                            output.append(end_line);
                            output.push_back('\n');
                        }
                    }
                    else if constexpr (std::is_same_v<NodeT, StrEntry>) {
                        if (!node_ptr->end_token.empty()) {
                            const std::string end_line = detail::combine_text_and_comment(
                                node_ptr->end_token, node_ptr->end_comment
                            );
                            output.append(end_line);
                            output.push_back('\n');
                        }
                    }
                    }, frame.node);
                continue;
            }

            std::visit([&](const auto* node_ptr) {
                using NodeT = std::decay_t<decltype(*node_ptr)>;

                if constexpr (std::is_same_v<NodeT, ConstructLevel>) {
                    if (!node_ptr->comment.empty()) {
                        append_indented_text(output, node_ptr->comment, frame.level);
                    }

                    std::string header_joined;
                    for (const std::string_view part : {
                        std::string_view{ node_ptr->_class },
                            std::string_view{ node_ptr->name },
                            std::string_view{ node_ptr->identifier }
                    }) {
                        if (!part.empty()) {
                            if (!header_joined.empty()) {
                                header_joined.append(sep);
                            }
                            header_joined.append(part);
                        }
                    }

                    if (!header_joined.empty()) {
                        const std::string header_line = detail::combine_text_and_comment(
                            header_joined, node_ptr->header_comment
                        );
                        append_indented_text(output, detail::lstrip_view(header_line), frame.level);
                    }

                    stack.push_back(SerializationFrame{ node_ptr, frame.level, true });
                    const int inner_level = frame.level + 1;
                    for (auto it = node_ptr->items.rbegin(); it != node_ptr->items.rend(); ++it) {
                        stack.push_back(SerializationFrame{ to_serializable_ref(*it), inner_level, false });
                    }
                }
                else if constexpr (std::is_same_v<NodeT, ScriptNode>) {
                    if (!node_ptr->comment.empty()) {
                        append_indented_text(output, node_ptr->comment, frame.level);
                    }

                    std::string header_base = node_ptr->name;
                    if (!node_ptr->identifier.empty()) {
                        if (!header_base.empty()) {
                            header_base.push_back(' ');
                        }
                        header_base.append(node_ptr->identifier);
                    }
                    const std::string header_line = detail::combine_text_and_comment(
                        detail::trim_view(header_base), node_ptr->header_comment
                    );
                    append_indented_text(output, detail::lstrip_view(header_line), frame.level);

                    const int inner_level = frame.level + 1;
                    for (const auto& line : node_ptr->content) {
                        if (!line.empty()) {
                            append_indented_text(output, line, inner_level);
                        }
                        else {
                            output.push_back('\n');
                        }
                    }

                    if (!node_ptr->end_token.empty()) {
                        const std::string end_line = detail::combine_text_and_comment(
                            node_ptr->end_token, node_ptr->end_comment
                        );
                        append_indent(output, std::max(0, frame.level));
                        output.append(end_line);
                        output.push_back('\n');
                    }
                }
                else if constexpr (std::is_same_v<NodeT, StrEntry>) {
                    if (!node_ptr->comment.empty()) {
                        append_indented_text(output, node_ptr->comment, 0);
                    }

                    const std::string header = !node_ptr->identifier.empty()
                        ? (node_ptr->category + ":" + node_ptr->identifier)
                        : node_ptr->category;
                    const std::string header_line = detail::combine_text_and_comment(header, node_ptr->header_comment);
                    output.append(header_line);
                    output.push_back('\n');

                    stack.push_back(SerializationFrame{ node_ptr, frame.level, true });
                    for (auto it = node_ptr->items.rbegin(); it != node_ptr->items.rend(); ++it) {
                        stack.push_back(SerializationFrame{ to_serializable_ref(*it), 1, false });
                    }
                }
                else if constexpr (std::is_same_v<NodeT, StatementNode>) {
                    append_indented_text(
                        output,
                        detail::combine_text_and_comment(node_ptr->text, node_ptr->comment),
                        frame.level
                    );
                }
                else if constexpr (std::is_same_v<NodeT, IncludeNode>) {
                    std::string directive = "#include " + node_ptr->raw_path;
                    append_indented_text(
                        output,
                        detail::combine_text_and_comment(directive, node_ptr->comment),
                        frame.level
                    );
                }
                else if constexpr (std::is_same_v<NodeT, DefineNode>) {
                    std::string directive = node_ptr->text.starts_with("#define")
                        ? node_ptr->text
                        : ("#define " + node_ptr->text);
                    append_indented_text(
                        output,
                        detail::combine_text_and_comment(directive, node_ptr->comment),
                        frame.level
                    );
                }
                else if constexpr (std::is_same_v<NodeT, CommentNode>) {
                    append_indented_text(output, node_ptr->text, frame.level);
                }
                }, frame.node);
        }

        return output;
    }

    std::string ScriptNode::print(int level, std::string_view file_type) const {
        const SerializableNodeRef ref{ this };
        return serialize_iterative(std::span<const SerializableNodeRef>{&ref, 1}, level, file_type);
    }

    std::string ConstructLevel::print(int level, std::string_view file_type) const {
        const SerializableNodeRef ref{ this };
        return serialize_iterative(std::span<const SerializableNodeRef>{&ref, 1}, level, file_type);
    }

    std::string StrEntry::print() const {
        const SerializableNodeRef ref{ this };
        return serialize_iterative(std::span<const SerializableNodeRef>{&ref, 1}, 0, ".str");
    }

    std::string StrDocument::print() const {
        std::string output;
        for (const auto& entry : entries) {
            const SerializableNodeRef ref = to_serializable_ref(entry);
            output.append(serialize_iterative(std::span<const SerializableNodeRef>{&ref, 1}, 0, ".str"));
            output.push_back('\n');
        }
        return output;
    }

    std::string ConstructFile::print() const {
        std::string output;

        bool has_define_nodes = false;
        for (const auto& item : items) {
            if (const auto* ast_ptr = std::get_if<AstNode>(&item)) {
                if (std::holds_alternative<DefineNode>(*ast_ptr)) {
                    has_define_nodes = true;
                    break;
                }
            }
        }

        if (!has_define_nodes) {
            for (const auto& def_line : defines) {
                output.append(def_line);
                output.push_back('\n');
            }
        }

        const std::string_view file_type = name.size() >= 4
            ? std::string_view{ name }.substr(name.size() - 4)
            : std::string_view{ ".ini" };

        for (const auto& item : items) {
            const SerializableNodeRef ref = to_serializable_ref(item);
            output.append(serialize_iterative(std::span<const SerializableNodeRef>{&ref, 1}, start_level, file_type));
            if (!std::holds_alternative<const DefineNode*>(ref)) {
                output.push_back('\n');
            }
        }
        return output;
    }

} // namespace lotm::ini
