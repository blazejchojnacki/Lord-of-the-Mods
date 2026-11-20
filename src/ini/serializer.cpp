/**
 * @file src/ini/serializer.cpp
 * @brief Implementation of iterative AST serialization and configurable formatting rules.
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

        void append_indent(std::string& out, int level, std::string_view indent_unit) {
            for (int i = 0; i < level; ++i) {
                out.append(indent_unit);
            }
        }

        void append_indented_text(std::string& out, std::string_view text, int level, std::string_view indent_unit) {
            const int safe_level = std::max(0, level);
            if (text.find('\n') != std::string_view::npos) {
                std::size_t pos = 0;
                while (pos <= text.size()) {
                    const std::size_t next_nl = text.find('\n', pos);
                    const std::string_view slice = (next_nl == std::string_view::npos)
                        ? text.substr(pos)
                        : text.substr(pos, next_nl - pos);

                    append_indent(out, safe_level, indent_unit);
                    out.append(detail::lstrip_view(slice));
                    out.push_back('\n');

                    if (next_nl == std::string_view::npos) {
                        break;
                    }
                    pos = next_nl + 1;
                }
                return;
            }

            append_indent(out, safe_level, indent_unit);
            out.append(text);
            out.push_back('\n');
        }

        [[nodiscard]] std::string format_single_comment(std::string_view raw, bool normalize_comments) {
            if (!normalize_comments || raw.empty()) {
                return std::string{ raw };
            }

            const std::string_view trimmed = detail::trim_view(raw);
            if (trimmed.empty()) {
                return {};
            }

            std::string_view body;
            if (trimmed.starts_with("//")) {
                body = detail::lstrip_view(trimmed.substr(2));
            }
            else if (trimmed.starts_with(';')) {
                body = detail::lstrip_view(trimmed.substr(1));
            }
            else {
                return std::string{ trimmed };
            }

            if (body.empty()) {
                return ";";
            }

            std::string out;
            out.reserve(2 + body.size());
            out.append("; ");
            out.append(body);
            return out;
        }

        [[nodiscard]] std::string format_comment_block(std::string_view raw, bool normalize_comments) {
            if (!normalize_comments || raw.empty()) {
                return std::string{ raw };
            }
            if (raw.find('\n') == std::string_view::npos) {
                return format_single_comment(raw, true);
            }

            std::string result;
            result.reserve(raw.size() + 8);
            std::size_t pos = 0;
            while (pos <= raw.size()) {
                const std::size_t next_nl = raw.find('\n', pos);
                const std::string_view line = (next_nl == std::string_view::npos)
                    ? raw.substr(pos)
                    : raw.substr(pos, next_nl - pos);

                if (pos > 0) {
                    result.push_back('\n');
                }
                result.append(format_single_comment(line, true));

                if (next_nl == std::string_view::npos) {
                    break;
                }
                pos = next_nl + 1;
            }
            return result;
        }

        [[nodiscard]] std::string format_statement_text(std::string_view text, bool normalize_equals) {
            if (!normalize_equals || text.empty()) {
                return std::string{ text };
            }

            bool in_quotes = false;
            std::size_t eq_pos = std::string_view::npos;
            for (std::size_t i = 0; i < text.size(); ++i) {
                const char c = text[i];
                if (c == '\\' && in_quotes && (i + 1) < text.size() && text[i + 1] == '"') {
                    ++i;
                    continue;
                }
                if (c == '"') {
                    in_quotes = !in_quotes;
                }
                else if (!in_quotes && c == '=') {
                    eq_pos = i;
                    break;
                }
            }

            if (eq_pos == std::string_view::npos) {
                return std::string{ text };
            }

            const std::string_view lhs = detail::trim_view(text.substr(0, eq_pos));
            const std::string_view rhs = detail::trim_view(text.substr(eq_pos + 1));

            std::string normalized;
            normalized.reserve(lhs.size() + 3 + rhs.size());
            normalized.append(lhs);
            if (rhs.empty()) {
                normalized.append(" =");
            }
            else {
                normalized.append(" = ");
                normalized.append(rhs);
            }
            return normalized;
        }

        [[nodiscard]] std::string format_header_part(std::string_view part, bool normalize_spacing) {
            if (!normalize_spacing || part.empty()) {
                return std::string{ part };
            }
            return detail::collapse_whitespace(part);
        }

        [[nodiscard]] std::string collapse_triple_newlines(std::string_view input) {
            std::string out;
            out.reserve(input.size());
            std::size_t consecutive_nl = 0;
            for (const char c : input) {
                if (c == '\n') {
                    ++consecutive_nl;
                    if (consecutive_nl <= 2) {
                        out.push_back(c);
                    }
                }
                else {
                    consecutive_nl = 0;
                    out.push_back(c);
                }
            }
            return out;
        }

    } // namespace

    std::string serialize_iterative(
        std::span<const SerializableNodeRef> items,
        int start_level,
        std::string_view file_type,
        const FormatOptions& options
    ) {
        std::string output;
        const std::string_view sep = detail::ends_with_ci(file_type, ".str") ? ":" : " ";
        const std::string_view indent_unit = options.indent;

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
                            const std::string end_tok = (options.normalize_end_tokens && is_ini_end(node_ptr->end_token))
                                ? std::string{ "End" }
                            : node_ptr->end_token;
                            const std::string end_cmt = format_single_comment(
                                node_ptr->end_comment, options.normalize_comments
                            );
                            const std::string end_line = detail::combine_text_and_comment(end_tok, end_cmt);
                            append_indent(output, std::max(0, frame.level), indent_unit);
                            output.append(end_line);
                            output.push_back('\n');
                        }
                    }
                    else if constexpr (std::is_same_v<NodeT, StrEntry>) {
                        if (!node_ptr->end_token.empty()) {
                            const std::string end_tok = (options.normalize_end_tokens && is_ini_end(node_ptr->end_token))
                                ? std::string{ "End" }
                            : node_ptr->end_token;
                            const std::string end_cmt = format_single_comment(
                                node_ptr->end_comment, options.normalize_comments
                            );
                            const std::string end_line = detail::combine_text_and_comment(end_tok, end_cmt);
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
                        const std::string lead_cmt = format_comment_block(
                            node_ptr->comment, options.normalize_comments
                        );
                        append_indented_text(output, lead_cmt, frame.level, indent_unit);
                    }

                    const std::string cls_part = format_header_part(node_ptr->_class, options.normalize_header_spacing);
                    const std::string name_part = format_header_part(node_ptr->name, options.normalize_header_spacing);
                    const std::string id_part = format_header_part(node_ptr->identifier, options.normalize_header_spacing);

                    std::string header_joined;
                    for (const std::string_view part : {
                        std::string_view{ cls_part },
                            std::string_view{ name_part },
                            std::string_view{ id_part }
                    }) {
                        if (!part.empty()) {
                            if (!header_joined.empty()) {
                                header_joined.append(sep);
                            }
                            header_joined.append(part);
                        }
                    }

                    if (!header_joined.empty()) {
                        const std::string hdr_cmt = format_single_comment(
                            node_ptr->header_comment, options.normalize_comments
                        );
                        const std::string header_line = detail::combine_text_and_comment(header_joined, hdr_cmt);
                        append_indented_text(output, detail::lstrip_view(header_line), frame.level, indent_unit);
                    }

                    stack.push_back(SerializationFrame{ node_ptr, frame.level, true });
                    const int inner_level = frame.level + 1;
                    for (auto it = node_ptr->items.rbegin(); it != node_ptr->items.rend(); ++it) {
                        stack.push_back(SerializationFrame{ to_serializable_ref(*it), inner_level, false });
                    }
                }
                else if constexpr (std::is_same_v<NodeT, ScriptNode>) {
                    if (!node_ptr->comment.empty()) {
                        const std::string lead_cmt = format_comment_block(
                            node_ptr->comment, options.normalize_comments
                        );
                        append_indented_text(output, lead_cmt, frame.level, indent_unit);
                    }

                    std::string header_base = options.normalize_header_spacing
                        ? std::string{ "BeginScript" }
                    : node_ptr->name;
                    const std::string ident_part = format_header_part(
                        node_ptr->identifier, options.normalize_header_spacing
                    );
                    if (!ident_part.empty()) {
                        if (!header_base.empty()) {
                            header_base.push_back(' ');
                        }
                        header_base.append(ident_part);
                    }
                    const std::string hdr_cmt = format_single_comment(
                        node_ptr->header_comment, options.normalize_comments
                    );
                    const std::string header_line = detail::combine_text_and_comment(
                        detail::trim_view(header_base), hdr_cmt
                    );
                    append_indented_text(output, detail::lstrip_view(header_line), frame.level, indent_unit);

                    const int inner_level = frame.level + 1;
                    for (const auto& line : node_ptr->content) {
                        if (!line.empty()) {
                            append_indented_text(output, line, inner_level, indent_unit);
                        }
                        else {
                            output.push_back('\n');
                        }
                    }

                    if (!node_ptr->end_token.empty()) {
                        const std::string end_tok = (options.normalize_end_tokens &&
                            detail::iequals_ascii(node_ptr->end_token, "endscript"))
                            ? std::string{ "EndScript" }
                        : node_ptr->end_token;
                        const std::string end_cmt = format_single_comment(
                            node_ptr->end_comment, options.normalize_comments
                        );
                        const std::string end_line = detail::combine_text_and_comment(end_tok, end_cmt);
                        append_indent(output, std::max(0, frame.level), indent_unit);
                        output.append(end_line);
                        output.push_back('\n');
                    }
                }
                else if constexpr (std::is_same_v<NodeT, StrEntry>) {
                    if (!node_ptr->comment.empty()) {
                        const std::string lead_cmt = format_comment_block(
                            node_ptr->comment, options.normalize_comments
                        );
                        append_indented_text(output, lead_cmt, 0, indent_unit);
                    }

                    const std::string cat_part = format_header_part(
                        node_ptr->category, options.normalize_header_spacing
                    );
                    const std::string id_part = format_header_part(
                        node_ptr->identifier, options.normalize_header_spacing
                    );
                    const std::string header = !id_part.empty()
                        ? (cat_part + ":" + id_part)
                        : cat_part;
                    const std::string hdr_cmt = format_single_comment(
                        node_ptr->header_comment, options.normalize_comments
                    );
                    const std::string header_line = detail::combine_text_and_comment(header, hdr_cmt);
                    output.append(header_line);
                    output.push_back('\n');

                    stack.push_back(SerializationFrame{ node_ptr, frame.level, true });
                    for (auto it = node_ptr->items.rbegin(); it != node_ptr->items.rend(); ++it) {
                        stack.push_back(SerializationFrame{ to_serializable_ref(*it), 1, false });
                    }
                }
                else if constexpr (std::is_same_v<NodeT, StatementNode>) {
                    const std::string stmt_text = format_statement_text(
                        node_ptr->text, options.normalize_statement_equals
                    );
                    const std::string stmt_cmt = format_single_comment(
                        node_ptr->comment, options.normalize_comments
                    );
                    append_indented_text(
                        output,
                        detail::combine_text_and_comment(stmt_text, stmt_cmt),
                        frame.level,
                        indent_unit
                    );
                }
                else if constexpr (std::is_same_v<NodeT, IncludeNode>) {
                    const std::string directive = "#include " + node_ptr->raw_path;
                    const std::string inc_cmt = format_single_comment(
                        node_ptr->comment, options.normalize_comments
                    );
                    append_indented_text(
                        output,
                        detail::combine_text_and_comment(directive, inc_cmt),
                        frame.level,
                        indent_unit
                    );
                }
                else if constexpr (std::is_same_v<NodeT, DefineNode>) {
                    const std::string directive = node_ptr->text.starts_with("#define")
                        ? node_ptr->text
                        : ("#define " + node_ptr->text);
                    const std::string def_cmt = format_single_comment(
                        node_ptr->comment, options.normalize_comments
                    );
                    append_indented_text(
                        output,
                        detail::combine_text_and_comment(directive, def_cmt),
                        frame.level,
                        indent_unit
                    );
                }
                else if constexpr (std::is_same_v<NodeT, CommentNode>) {
                    const std::string cmt_text = format_comment_block(
                        node_ptr->text, options.normalize_comments
                    );
                    append_indented_text(output, cmt_text, frame.level, indent_unit);
                }
                }, frame.node);
        }

        if (options.coalesce_blank_lines) {
            return collapse_triple_newlines(output);
        }
        return output;
    }

    std::string ScriptNode::print(
        int level,
        std::string_view file_type,
        const FormatOptions& options
    ) const {
        const SerializableNodeRef ref{ this };
        return serialize_iterative(std::span<const SerializableNodeRef>{&ref, 1}, level, file_type, options);
    }

    std::string ConstructLevel::print(
        int level,
        std::string_view file_type,
        const FormatOptions& options
    ) const {
        const SerializableNodeRef ref{ this };
        return serialize_iterative(std::span<const SerializableNodeRef>{&ref, 1}, level, file_type, options);
    }

    std::string StrEntry::print(const FormatOptions& options) const {
        const SerializableNodeRef ref{ this };
        return serialize_iterative(std::span<const SerializableNodeRef>{&ref, 1}, 0, ".str", options);
    }

    std::string StrDocument::print(const FormatOptions& options) const {
        std::string output;
        for (const auto& entry : entries) {
            const SerializableNodeRef ref = to_serializable_ref(entry);
            output.append(serialize_iterative(std::span<const SerializableNodeRef>{&ref, 1}, 0, ".str", options));
            output.push_back('\n');
        }
        if (options.coalesce_blank_lines) {
            return collapse_triple_newlines(output);
        }
        return output;
    }

    std::string ConstructFile::print(const FormatOptions& options) const {
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
            output.append(
                serialize_iterative(std::span<const SerializableNodeRef>{&ref, 1}, start_level, file_type, options)
            );
            if (!std::holds_alternative<const DefineNode*>(ref)) {
                output.push_back('\n');
            }
        }

        if (options.coalesce_blank_lines) {
            return collapse_triple_newlines(output);
        }
        return output;
    }

} // namespace lotm::ini
