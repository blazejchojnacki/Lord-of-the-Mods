/**
 * @file src/ini/parser.cpp
 * @brief Implementation of the SAGE INI/INC/STR parser, iterative serializer, and include validator.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "ini/parser.hpp"

#include <algorithm>
#include <fstream>
#include <iterator>
#include <sstream>

namespace lotm::ini {

    namespace {

        [[nodiscard]] bool ends_with_ci(std::string_view str, std::string_view suffix) noexcept {
            if (str.size() < suffix.size()) {
                return false;
            }
            return detail::iequals_ascii(str.substr(str.size() - suffix.size()), suffix);
        }

        [[nodiscard]] bool is_supported_config_ext(std::string_view path) noexcept {
            return ends_with_ci(path, ".ini") || ends_with_ci(path, ".inc") || ends_with_ci(path, ".str");
        }

        [[nodiscard]] std::string join_views(std::span<const std::string_view> tokens, std::string_view sep = " ") {
            if (tokens.empty()) {
                return {};
            }
            std::size_t total_len = sep.size() * (tokens.size() - 1);
            for (const auto tok : tokens) {
                total_len += tok.size();
            }
            std::string result;
            result.reserve(total_len);
            for (std::size_t i = 0; i < tokens.size(); ++i) {
                if (i > 0) {
                    result.append(sep);
                }
                result.append(tokens[i]);
            }
            return result;
        }

        [[nodiscard]] std::string combine_text_and_comment(std::string_view text, std::string_view comment) {
            if (!text.empty() && !comment.empty()) {
                std::string combined;
                combined.reserve(text.size() + 1 + comment.size());
                combined.append(text);
                combined.push_back(' ');
                combined.append(comment);
                return combined;
            }
            if (!text.empty()) {
                return std::string{ text };
            }
            return std::string{ comment };
        }

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

        [[nodiscard]] std::string read_file_bytes(const std::filesystem::path& path) {
            std::ifstream file(path, std::ios::binary | std::ios::ate);
            if (!file.is_open()) {
                throw IniParseError("file " + path.string() + " invalid.");
            }
            const auto end_pos = file.tellg();
            if (end_pos < 0) {
                throw IniParseError("failed to read file size: " + path.string());
            }
            std::string buffer(static_cast<std::size_t>(end_pos), '\0');
            file.seekg(0, std::ios::beg);
            if (!buffer.empty() && !file.read(buffer.data(), static_cast<std::streamsize>(buffer.size()))) {
                throw IniParseError("failed to read file contents: " + path.string());
            }
            return buffer;
        }

        [[nodiscard]] std::vector<std::vector<std::string>> materialize_delimiter_group(
            std::span<const std::span<const std::string_view>> group
        ) {
            std::vector<std::vector<std::string>> result;
            result.reserve(group.size() + 1);
            for (const auto& level : group) {
                std::vector<std::string> level_vec;
                level_vec.reserve(level.size());
                for (const auto kw : level) {
                    level_vec.emplace_back(kw);
                }
                result.push_back(std::move(level_vec));
            }
            result.emplace_back(); // Empty tail level
            return result;
        }

        [[nodiscard]] bool is_path_within_root(
            const std::filesystem::path& candidate,
            const std::filesystem::path& root
        ) {
            const auto cand_it_end = candidate.end();
            const auto root_it_end = root.end();

            auto cand_it = candidate.begin();
            auto root_it = root.begin();

            while (root_it != root_it_end) {
                if (cand_it == cand_it_end) {
                    return false;
                }
                if (*cand_it != *root_it) {
                    // Case-insensitive component comparison on Windows, exact on POSIX
#ifdef _WIN32
                    if (!detail::iequals_ascii(cand_it->string(), root_it->string())) {
                        return false;
                    }
#else
                    return false;
#endif
                }
                ++cand_it;
                ++root_it;
            }
            return true;
        }

    } // namespace

    std::string serialize_iterative(
        std::span<const SerializableNodeRef> items,
        int start_level,
        std::string_view file_type
    ) {
        std::string output;
        const std::string_view sep = (ends_with_ci(file_type, ".ini") || ends_with_ci(file_type, ".inc")) ? " " : ":";

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
                            const std::string end_line = combine_text_and_comment(
                                node_ptr->end_token, node_ptr->end_comment
                            );
                            append_indent(output, std::max(0, frame.level));
                            output.append(end_line);
                            output.push_back('\n');
                        }
                    }
                    else if constexpr (std::is_same_v<NodeT, StrEntry>) {
                        if (!node_ptr->end_token.empty()) {
                            const std::string end_line = combine_text_and_comment(
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
                        const std::string header_line = combine_text_and_comment(
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
                    const std::string header_line = combine_text_and_comment(
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
                        const std::string end_line = combine_text_and_comment(
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
                    const std::string header_line = combine_text_and_comment(header, node_ptr->header_comment);
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
                        combine_text_and_comment(node_ptr->text, node_ptr->comment),
                        frame.level
                    );
                }
                else if constexpr (std::is_same_v<NodeT, IncludeNode>) {
                    std::string directive = "#include " + node_ptr->raw_path;
                    append_indented_text(
                        output,
                        combine_text_and_comment(directive, node_ptr->comment),
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

    std::pair<std::vector<std::vector<std::string>>, int> recognize_structure(
        std::string_view file_path,
        std::optional<std::string_view> file_content
    ) {
        if (ends_with_ci(file_path, ".str")) {
            std::vector<std::string> str_delims;
            str_delims.reserve(STR_DELIMITERS.size());
            for (const auto kw : STR_DELIMITERS) {
                str_delims.emplace_back(kw);
            }
            return { { std::move(str_delims), std::vector<std::string>{} }, 0 };
        }

        if (ends_with_ci(file_path, ".ini") || ends_with_ci(file_path, ".inc")) {
            std::string owned_buffer;
            std::string_view content_view;
            if (file_content.has_value()) {
                content_view = *file_content;
            }
            else {
                owned_buffer = read_file_bytes(std::filesystem::path{ file_path });
                content_view = owned_buffer;
            }

            const bool is_ini = ends_with_ci(file_path, ".ini");
            std::pair<std::vector<std::vector<std::string>>, int> matched_result{ {}, 0 };
            LexedLine lexed;

            for_each_line_view(content_view, [&](std::string_view raw_line, std::size_t) -> bool {
                lex_line_into(raw_line, lexed);
                if (lexed.line_tokens.empty()) {
                    return true;
                }

                for (std::size_t group_idx = 0; group_idx < INI_DELIMITER_RULES.size(); ++group_idx) {
                    const auto& group_rules = INI_DELIMITER_RULES[group_idx];
                    for (std::size_t level_idx = 0; level_idx < group_rules.size(); ++level_idx) {
                        if (is_ini && level_idx > 0) {
                            break;
                        }
                        if (match_delimiter_rule(lexed.line_tokens, group_rules[level_idx]) != nullptr) {
                            matched_result = {
                                materialize_delimiter_group(INI_DELIMITERS[group_idx]),
                                static_cast<int>(level_idx)
                            };
                            return false; // Stop iterating lines
                        }
                    }
                }
                return true;
                });

            return matched_result;
        }

        return { {}, 0 };
    }

    std::filesystem::path validate_include(
        const IncludeNode& node,
        const std::filesystem::path& current_file,
        const std::filesystem::path& virtual_root
    ) {
        const std::string clean = node.clean_path();
        const std::filesystem::path target_rel{ clean };

        std::error_code ec;
        const std::filesystem::path canon_root = std::filesystem::weakly_canonical(virtual_root, ec);
        if (ec) {
            throw IniParseError("Invalid virtual root: " + virtual_root.string());
        }

        std::filesystem::path candidate = std::filesystem::weakly_canonical(
            current_file.parent_path() / target_rel, ec
        );
        if (ec || !std::filesystem::is_regular_file(candidate, ec)) {
            candidate = std::filesystem::weakly_canonical(canon_root / target_rel, ec);
        }

        if (!is_path_within_root(candidate, canon_root)) {
            throw IniParseError(
                "Security violation: " + node.raw_path + " escapes virtual root " + virtual_root.string()
            );
        }

        if (!std::filesystem::is_regular_file(candidate, ec)) {
            throw IniParseError("Include file not found: " + node.raw_path);
        }

        return candidate;
    }

    StrDocument StrParser::parse_file(
        std::string_view file_path,
        bool strict,
        std::optional<std::string_view> file_content
    ) {
        if (!ends_with_ci(file_path, ".str") ||
            (!file_content.has_value() && !std::filesystem::is_regular_file(std::filesystem::path{ file_path }))) {
            throw IniParseError("file " + std::string{ file_path } + " invalid.");
        }

        std::string owned_buffer;
        std::string_view content_view;
        if (file_content.has_value()) {
            content_view = *file_content;
        }
        else {
            owned_buffer = read_file_bytes(std::filesystem::path{ file_path });
            content_view = owned_buffer;
        }

        StrDocument doc;
        doc.name = std::string{ file_path };

        std::optional<StrEntry> active_entry = std::nullopt;
        std::string last_comment;
        LexedLine lexed;

        for_each_line_view(content_view, [&](std::string_view raw_line, std::size_t line_num) {
            lex_line_into(raw_line, lexed);

            if (lexed.words.empty()) {
                if (!lexed.comment.empty()) {
                    if (!last_comment.empty()) {
                        last_comment.push_back('\n');
                    }
                    last_comment.append(lexed.comment);
                }
                if (!last_comment.empty() && detail::trim_view(raw_line).empty()) {
                    if (active_entry.has_value()) {
                        active_entry->items.emplace_back(CommentNode{ std::move(last_comment) });
                    }
                    else {
                        doc.entries.emplace_back(CommentNode{ std::move(last_comment) });
                    }
                    last_comment.clear();
                }
                return;
            }

            const DelimiterRule* matched_rule = match_delimiter_rule(lexed.line_tokens, STR_DELIMITER_RULES);
            if (matched_rule != nullptr) {
                if (active_entry.has_value()) {
                    const std::string active_id = active_entry->identifier.empty()
                        ? active_entry->category
                        : (active_entry->category + ":" + active_entry->identifier);
                    std::string err_msg = "Delimiter mismatch: unclosed entry '" + active_id +
                        "' before starting new entry at " + std::string{ file_path } + ":" + std::to_string(line_num);
                    doc.errors.push_back(err_msg);
                    if (strict) {
                        throw IniParseError(err_msg);
                    }
                    doc.entries.emplace_back(std::move(*active_entry));
                    active_entry.reset();
                }

                const auto remaining = std::span<const std::string_view>{ lexed.words }.subspan(
                    std::min(matched_rule->word_count, lexed.words.size())
                );

                std::string cat{ matched_rule->raw };
                std::string ident = join_views(remaining);
                validate_sage_bounds(cat, ident);

                active_entry = StrEntry{
                    std::move(cat),
                    std::move(ident),
                    std::move(last_comment),
                    lexed.comment,
                    "End",
                    "",
                    {}
                };
                last_comment.clear();
                return;
            }

            if (!last_comment.empty()) {
                if (active_entry.has_value()) {
                    active_entry->items.emplace_back(CommentNode{ std::move(last_comment) });
                }
                else {
                    doc.entries.emplace_back(CommentNode{ std::move(last_comment) });
                }
                last_comment.clear();
            }

            if (is_ini_end(lexed.words[0])) {
                if (!active_entry.has_value()) {
                    std::string err_msg = "Delimiter mismatch: negative level reached at " +
                        std::string{ file_path } + ":" + std::to_string(line_num) +
                        " on closing keyword '" + std::string{ lexed.words[0] } + "': " +
                        std::string{ detail::trim_view(raw_line) };
                    doc.errors.push_back(err_msg);
                    if (strict) {
                        throw IniParseError(err_msg);
                    }
                    doc.entries.emplace_back(StatementNode{ join_views(lexed.words), lexed.comment });
                }
                else {
                    active_entry->end_token = join_views(lexed.words);
                    active_entry->end_comment = lexed.comment;
                    doc.entries.emplace_back(std::move(*active_entry));
                    active_entry.reset();
                }
                return;
            }

            StatementNode stmt{ join_views(lexed.words_signs), lexed.comment };
            if (active_entry.has_value()) {
                active_entry->items.emplace_back(std::move(stmt));
            }
            else {
                std::string err_msg = "Unexpected statement outside entry at " +
                    std::string{ file_path } + ":" + std::to_string(line_num) +
                    ": " + std::string{ detail::trim_view(raw_line) };
                doc.errors.push_back(err_msg);
                if (strict) {
                    throw IniParseError(err_msg);
                }
                doc.entries.emplace_back(std::move(stmt));
            }
            });

        if (!last_comment.empty()) {
            if (active_entry.has_value()) {
                active_entry->items.emplace_back(CommentNode{ std::move(last_comment) });
            }
            else {
                doc.entries.emplace_back(CommentNode{ std::move(last_comment) });
            }
            last_comment.clear();
        }

        if (active_entry.has_value()) {
            const std::string active_id = active_entry->identifier.empty()
                ? active_entry->category
                : (active_entry->category + ":" + active_entry->identifier);
            std::string err_msg = "Unexpected EOF in " + std::string{ file_path } +
                ": unclosed entry '" + active_id + "' remains.";
            doc.errors.push_back(err_msg);
            if (strict) {
                throw IniParseError(err_msg);
            }
            doc.entries.emplace_back(std::move(*active_entry));
        }

        return doc;
    }

    ConstructFile::ConstructFile(
        std::string file_name,
        bool is_strict,
        std::optional<std::string> content
    )
        : name(std::move(file_name)),
        strict(is_strict),
        file_content(std::move(content)) {
        if (!name.empty()) {
            construct();
        }
    }

    void ConstructFile::construct() {
        if (!is_supported_config_ext(name) ||
            (!file_content.has_value() && !std::filesystem::is_regular_file(std::filesystem::path{ name }))) {
            throw IniParseError("file " + name + " invalid.");
        }

        items.clear();
        defines.clear();
        errors.clear();
        last_comment.clear();
        context_stack_.clear();
        context_stack_.emplace_back(this);

        if (ends_with_ci(name, ".str")) {
            const std::optional<std::string_view> content_opt = file_content.has_value()
                ? std::optional<std::string_view>{*file_content}
            : std::nullopt;
            StrDocument str_doc = StrParser::parse_file(name, strict, content_opt);

            std::vector<std::string> str_delims;
            str_delims.reserve(STR_DELIMITERS.size());
            for (const auto kw : STR_DELIMITERS) {
                str_delims.emplace_back(kw);
            }
            delimiters = { std::move(str_delims), std::vector<std::string>{} };
            start_level = 0;

            items.reserve(str_doc.entries.size());
            for (auto& entry : str_doc.entries) {
                std::visit([&](auto&& concrete) {
                    using T = std::decay_t<decltype(concrete)>;
                    if constexpr (std::is_same_v<T, StrEntry>) {
                        items.emplace_back(std::move(concrete));
                    }
                    else {
                        items.emplace_back(AstNode{ std::move(concrete) });
                    }
                    }, std::move(entry));
            }
            errors = std::move(str_doc.errors);
            return;
        }

        std::string owned_buffer;
        std::string_view content_view;
        if (file_content.has_value()) {
            content_view = *file_content;
        }
        else {
            owned_buffer = read_file_bytes(std::filesystem::path{ name });
            content_view = owned_buffer;
        }

        auto [recognized_delims, recognized_start] = recognize_structure(name, content_view);
        delimiters = std::move(recognized_delims);
        start_level = recognized_start;

        active_rules_.clear();
        active_rules_.reserve(delimiters.size());
        for (const auto& level : delimiters) {
            active_rules_.push_back(compile_delimiter_rules(level));
        }
        current_level = start_level;

        LexedLine lex_scratch;
        for_each_line_view(content_view, [&](std::string_view raw_line, std::size_t line_num) {
            parse_line(raw_line, line_num, lex_scratch);
            });

        if (!last_comment.empty()) {
            append_to_active_context(CommentNode{ std::move(last_comment) });
            last_comment.clear();
        }

        if (current_level != start_level) {
            std::string err_msg = "Unexpected EOF in " + name + ": unclosed block(s) remain (current_level " +
                std::to_string(current_level) + " != start_level " + std::to_string(start_level) + ").";
            errors.push_back(err_msg);
            if (strict) {
                throw IniParseError(err_msg);
            }
        }
    }

    int ConstructFile::get_lookup_level() const noexcept {
        int shift = 0;
        for (const auto& ctx : context_stack_) {
            if (const auto* lvl_ptr = std::get_if<ConstructLevel*>(&ctx)) {
                if ((*lvl_ptr)->_class == "ReplaceModule" || (*lvl_ptr)->_class == "ReplaceModule =") {
                    ++shift;
                }
            }
        }
        return std::max(0, current_level - shift);
    }

    void ConstructFile::append_to_active_context(AstNode node) {
        std::visit([&](auto* ptr) {
            using PtrT = std::decay_t<decltype(ptr)>;
            if constexpr (std::is_same_v<PtrT, ConstructFile*>) {
                ptr->append(std::move(node));
            }
            else if constexpr (std::is_same_v<PtrT, ConstructLevel*>) {
                ptr->append(std::move(node));
            }
            }, context_stack_.back());
    }

    void ConstructFile::parse_line(std::string_view raw_line, std::size_t line_num, LexedLine& lexed) {
        lex_line_into(raw_line, lexed);

        if (auto* script_ptr = std::get_if<ScriptNode*>(&context_stack_.back())) {
            ScriptNode* active_script = *script_ptr;
            if (!lexed.words.empty() && detail::iequals_ascii(lexed.words[0], "endscript")) {
                active_script->end_token = join_views(lexed.words);
                active_script->end_comment = lexed.comment;
                context_stack_.pop_back();
                --current_level;
            }
            else {
                active_script->content.emplace_back(detail::trim_view(raw_line));
            }
            return;
        }

        if (lexed.words.empty()) {
            if (!lexed.comment.empty()) {
                if (!last_comment.empty()) {
                    last_comment.push_back('\n');
                }
                last_comment.append(lexed.comment);
            }
            handle_empty_line(raw_line);
            return;
        }

        if (detail::iequals_ascii(lexed.words[0], "beginscript")) {
            if (current_level >= static_cast<int>(MAX_INI_DEPTH)) {
                throw IniParseError(
                    "Security abort: Maximum INI depth (" + std::to_string(MAX_INI_DEPTH) +
                    ") exceeded in " + name + "."
                );
            }

            const auto ident_span = std::span<const std::string_view>{ lexed.words }.subspan(1);

            std::string n{ lexed.words[0] };
            std::string ident = join_views(ident_span);
            validate_sage_bounds(n, ident);

            ScriptNode new_script{
                std::move(n),
                std::move(ident),
                std::move(last_comment),
                lexed.comment,
                "EndScript",
                "",
                {}
            };

            ScriptNode* pushed_script = nullptr;
            std::visit([&](auto* ptr) {
                using PtrT = std::decay_t<decltype(ptr)>;
                if constexpr (std::is_same_v<PtrT, ConstructFile*>) {
                    ptr->items.emplace_back(AstNode{ std::move(new_script) });
                    pushed_script = &std::get<ScriptNode>(std::get<AstNode>(ptr->items.back()));
                }
                else if constexpr (std::is_same_v<PtrT, ConstructLevel*>) {
                    ptr->items.emplace_back(std::move(new_script));
                    pushed_script = &std::get<ScriptNode>(ptr->items.back());
                }
                }, context_stack_.back());

            context_stack_.emplace_back(pushed_script);
            last_comment.clear();
            ++current_level;
            return;
        }

        // Intercept dynamically keyed FCurve blocks (e.g. "Alpha = FCurve")
        if (lexed.line_tokens.size() >= 3 &&
            lexed.line_tokens[1] == "=" &&
            detail::iequals_ascii(lexed.line_tokens[2], "fcurve")) {
            if (current_level >= static_cast<int>(MAX_INI_DEPTH)) {
                throw IniParseError(
                    "Security abort: Maximum INI depth (" + std::to_string(MAX_INI_DEPTH) +
                    ") exceeded in " + name + "."
                );
            }

            const auto ident_span = lexed.words.size() >= 2
                ? std::span<const std::string_view>{lexed.words}.subspan(2)
                : std::span<const std::string_view>{};

            std::string class_str = std::string{ lexed.words[0] } + " =";
            std::string block_name = lexed.words.size() >= 2 ? std::string{ lexed.words[1] } : std::string{};
            std::string ident = join_views(ident_span);
            validate_sage_bounds(block_name, ident);

            ConstructLevel new_fcurve{
                std::move(class_str),
                std::move(block_name),
                std::move(ident),
                std::move(last_comment),
                lexed.comment
            };

            ConstructLevel* pushed_level = nullptr;
            std::visit([&](auto* ptr) {
                using PtrT = std::decay_t<decltype(ptr)>;
                if constexpr (std::is_same_v<PtrT, ConstructFile*>) {
                    ptr->items.emplace_back(AstNode{ std::move(new_fcurve) });
                    pushed_level = &std::get<ConstructLevel>(std::get<AstNode>(ptr->items.back()));
                }
                else if constexpr (std::is_same_v<PtrT, ConstructLevel*>) {
                    ptr->items.emplace_back(std::move(new_fcurve));
                    pushed_level = &std::get<ConstructLevel>(ptr->items.back());
                }
                }, context_stack_.back());

            context_stack_.emplace_back(pushed_level);
            last_comment.clear();
            ++current_level;
            return;
        }

        if (handle_block_start(lexed.words, lexed.line_tokens, lexed.comment)) {
            return;
        }

        // At base level, check if the line starts a block from a different schema group
        if (current_level == start_level && !is_ini_end(lexed.words[0]) && !lexed.words[0].starts_with('#')) {
            for (std::size_t group_idx = 0; group_idx < INI_DELIMITER_RULES.size(); ++group_idx) {
                const auto& group_rules = INI_DELIMITER_RULES[group_idx];
                if (!group_rules.empty() && match_delimiter_rule(lexed.line_tokens, group_rules[0]) != nullptr) {
                    delimiters = materialize_delimiter_group(INI_DELIMITERS[group_idx]);
                    active_rules_.clear();
                    active_rules_.reserve(delimiters.size());
                    for (const auto& level : delimiters) {
                        active_rules_.push_back(compile_delimiter_rules(level));
                    }
                    if (handle_block_start(lexed.words, lexed.line_tokens, lexed.comment)) {
                        return;
                    }
                }
            }
        }

        if (!last_comment.empty()) {
            append_to_active_context(CommentNode{ std::move(last_comment) });
            last_comment.clear();
        }

        if (handle_block_end(lexed.words, line_num, raw_line, lexed.comment)) {
            return;
        }

        if (handle_directives(lexed.words, lexed.words_signs, lexed.comment)) {
            return;
        }

        handle_statement(lexed.words_signs, lexed.comment);
    }

    void ConstructFile::handle_empty_line(std::string_view raw_line) {
        if (!last_comment.empty() && detail::trim_view(raw_line).empty()) {
            append_to_active_context(CommentNode{ std::move(last_comment) });
            last_comment.clear();
        }
    }

    bool ConstructFile::handle_block_start(
        std::span<const std::string_view> words,
        std::span<const std::string_view> line_tokens,
        std::string_view inline_comment
    ) {
        const auto lookup_level = static_cast<std::size_t>(get_lookup_level());
        if (lookup_level >= active_rules_.size()) {
            return false;
        }

        const DelimiterRule* matched_rule = match_delimiter_rule(line_tokens, active_rules_[lookup_level]);
        if (matched_rule == nullptr) {
            return false;
        }

        if (current_level >= static_cast<int>(MAX_INI_DEPTH)) {
            throw IniParseError(
                "Security abort: Maximum INI depth (" + std::to_string(MAX_INI_DEPTH) +
                ") exceeded in " + name + "."
            );
        }

        const auto remaining_words = words.subspan(std::min(matched_rule->word_count, words.size()));

        std::string block_name;
        std::string block_identifier;
        if (remaining_words.size() == 2 && (ends_with_ci(name, ".ini") || ends_with_ci(name, ".inc"))) {
            block_name = std::string{ remaining_words[0] };
            block_identifier = std::string{ remaining_words[1] };
        }
        else if (!remaining_words.empty()) {
            block_name = join_views(remaining_words);
        }

        std::string class_token{ matched_rule->raw };
        const std::size_t next_idx = matched_rule->token_count;
        if (next_idx < line_tokens.size() && line_tokens[next_idx] == "=" && !class_token.ends_with('=')) {
            class_token.append(" =");
        }

        validate_sage_bounds(block_name, block_identifier);

        ConstructLevel new_block{
            std::move(class_token),
            std::move(block_name),
            std::move(block_identifier),
            std::move(last_comment),
            std::string{ inline_comment }
        };

        ConstructLevel* pushed_level = nullptr;
        std::visit([&](auto* ptr) {
            using PtrT = std::decay_t<decltype(ptr)>;
            if constexpr (std::is_same_v<PtrT, ConstructFile*>) {
                ptr->items.emplace_back(AstNode{ std::move(new_block) });
                pushed_level = &std::get<ConstructLevel>(std::get<AstNode>(ptr->items.back()));
            }
            else if constexpr (std::is_same_v<PtrT, ConstructLevel*>) {
                ptr->items.emplace_back(std::move(new_block));
                pushed_level = &std::get<ConstructLevel>(ptr->items.back());
            }
            }, context_stack_.back());

        context_stack_.emplace_back(pushed_level);
        last_comment.clear();
        ++current_level;
        return true;
    }

    bool ConstructFile::handle_block_end(
        std::span<const std::string_view> words,
        std::size_t line_num,
        std::string_view raw_line,
        std::string_view inline_comment
    ) {
        if (!is_ini_end(words[0])) {
            return false;
        }

        --current_level;
        if (current_level < 0) {
            std::string err_msg = "Delimiter mismatch: negative level reached at " +
                name + ":" + std::to_string(line_num) +
                " on closing keyword '" + std::string{ words[0] } + "': " +
                std::string{ detail::trim_view(raw_line) };
            errors.push_back(err_msg);
            if (strict) {
                throw IniParseError(err_msg);
            }
            current_level = 0;
        }

        std::string end_str = join_views(words);
        if (context_stack_.size() > 1) {
            if (auto* lvl_ptr = std::get_if<ConstructLevel*>(&context_stack_.back())) {
                (*lvl_ptr)->end_token = std::move(end_str);
                (*lvl_ptr)->end_comment = std::string{ inline_comment };
                context_stack_.pop_back();
                return true;
            }
        }

        append_to_active_context(StatementNode{ std::move(end_str), std::string{ inline_comment } });
        return true;
    }

    bool ConstructFile::handle_directives(
        std::span<const std::string_view> words,
        std::span<const std::string_view> words_signs,
        std::string_view inline_comment
    ) {
        if (words[0] == "#define") {
            defines.push_back(combine_text_and_comment(join_views(words_signs), inline_comment));
            return true;
        }
        if (words[0] == "#include") {
            const std::string raw_path = words_signs.size() > 1
                ? join_views(words_signs.subspan(1))
                : std::string{};
            append_to_active_context(IncludeNode{ raw_path, std::string{ inline_comment } });
            return true;
        }
        return false;
    }

    void ConstructFile::handle_statement(
        std::span<const std::string_view> words_signs,
        std::string_view inline_comment
    ) {
        append_to_active_context(StatementNode{ join_views(words_signs), std::string{ inline_comment } });
    }

    std::string ConstructFile::print() const {
        std::string output;
        for (const auto& def_line : defines) {
            output.append(def_line);
            output.push_back('\n');
        }

        const std::string_view file_type = name.size() >= 4
            ? std::string_view{ name }.substr(name.size() - 4)
            : std::string_view{ ".ini" };

        for (const auto& item : items) {
            const SerializableNodeRef ref = to_serializable_ref(item);
            output.append(serialize_iterative(std::span<const SerializableNodeRef>{&ref, 1}, start_level, file_type));
            output.push_back('\n');
        }
        return output;
    }

    std::pair<std::string, std::vector<std::vector<std::string>>> load_file(std::string_view full_path) {
        if (full_path.empty()) {
            throw IniParseError("empty path.");
        }
        const std::filesystem::path fs_path{ full_path };
        if (!std::filesystem::is_regular_file(fs_path)) {
            throw IniParseError("wrong path: " + std::string{ full_path });
        }

        if (is_supported_config_ext(full_path)) {
            try {
                ConstructFile file_object{ std::string{ full_path }, false };
                std::string printed = file_object.print();
                if (printed.empty()) {
                    return { read_file_bytes(fs_path),{} };
                }
                return { std::move(printed), std::move(file_object.delimiters) };
            }
            catch (const IniParseError&) {
                return { read_file_bytes(fs_path),{} };
            }
            catch (const std::out_of_range&) {
                return { read_file_bytes(fs_path),{} };
            }
        }

        if (ends_with_ci(full_path, ".txt")) {
            return { read_file_bytes(fs_path),{} };
        }

        throw IniParseError("wrong path or unsupported file type: " + std::string{ full_path });
    }

    std::vector<std::string> scan_file_for_errors(std::string_view file_path) {
        try {
            ConstructFile file_object{ std::string{ file_path }, false };
            return file_object.errors;
        }
        catch (const std::exception& exc) {
            return { "Fatal error while processing " + std::string{ file_path } + ": " + exc.what() };
        }
    }

} // namespace lotm::ini
