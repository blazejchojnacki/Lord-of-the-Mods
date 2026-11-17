/**
 * @file src/ini/ini_parser.cpp
 * @brief Implementation of the structural SAGE.ini and .inc parser and structure recognizer.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "parser_utils.hpp"
#include "ini/parser.hpp"
#include <core/path_utils.hpp>

#include <algorithm>
#include <filesystem>
#include <optional>
#include <span>
#include <stdexcept>

namespace lotm::ini {

    namespace {

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

        [[nodiscard]] std::pair<std::vector<std::vector<std::string>>, int> recognize_structure_from_utf8(
            std::string_view file_path,
            std::string_view content_view
        ) {
            const bool is_ini = detail::ends_with_ci(file_path, ".ini");
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

    } // namespace

    std::pair<std::vector<std::vector<std::string>>, int> recognize_structure(
        std::string_view file_path,
        std::optional<std::string_view> file_content
    ) {
        if (detail::ends_with_ci(file_path, ".str")) {
            std::vector<std::string> str_delims;
            str_delims.reserve(STR_DELIMITERS.size());
            for (const auto kw : STR_DELIMITERS) {
                str_delims.emplace_back(kw);
            }
            return { { std::move(str_delims), std::vector<std::string>{} }, 0 };
        }

        if (detail::ends_with_ci(file_path, ".ini") || detail::ends_with_ci(file_path, ".inc")) {
            std::optional<detail::MMapFile> mmap;
            std::string transcoded_buffer;
            std::string_view raw_view;
            if (file_content.has_value()) {
                raw_view = *file_content;
            }
            else {
                mmap.emplace(lotm::core::utf8_to_path(file_path));
                raw_view = mmap->view();
            }
            const std::string_view content_view = detail::prepare_utf8_view(raw_view, transcoded_buffer);
            return recognize_structure_from_utf8(file_path, content_view);
        }

        return { {}, 0 };
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

    ConstructFile::ConstructFile(
        std::string file_name,
        bool is_strict,
        std::span<const uint8_t> buffer
    )
        : name(std::move(file_name)),
        strict(is_strict) {
        if (!name.empty()) {
            if (!detail::is_supported_config_ext(name)) {
                throw IniParseError("file " + name + " invalid.");
            }
            const std::string_view raw_view(
                buffer.empty() ? "" : reinterpret_cast<const char*>(buffer.data()),
                buffer.size()
            );
            std::string transcoded;
            const std::string_view utf8_view = detail::prepare_utf8_view(raw_view, transcoded);
            construct_from_utf8_view(utf8_view, false);
        }
    }

    void ConstructFile::construct() {
        const std::filesystem::path fs_path = lotm::core::utf8_to_path(name);
        if (!detail::is_supported_config_ext(name) ||
            (!file_content.has_value() && !std::filesystem::is_regular_file(fs_path))) {
            throw IniParseError("file " + name + " invalid.");
        }

        if (file_content.has_value()) {
            std::string transcoded;
            const std::string_view utf8_view = detail::prepare_utf8_view(*file_content, transcoded);
            if (!transcoded.empty()) {
                *file_content = std::move(transcoded);
            }
            else if (utf8_view.size() != file_content->size()) {
                *file_content = std::string{ utf8_view };
            }
            construct_from_utf8_view(*file_content, false);
            return;
        }

        detail::MMapFile mmap{ fs_path };
        std::string transcoded;
        const std::string_view utf8_view = detail::prepare_utf8_view(mmap.view(), transcoded);
        construct_from_utf8_view(utf8_view, false);
    }

    void ConstructFile::construct_with_metadata() {
        const std::filesystem::path fs_path = lotm::core::utf8_to_path(name);
        if (!detail::is_supported_config_ext(name) ||
            (!file_content.has_value() && !std::filesystem::is_regular_file(fs_path))) {
            throw IniParseError("file " + name + " invalid.");
        }

        if (file_content.has_value()) {
            std::string transcoded;
            const std::string_view utf8_view = detail::prepare_utf8_view(*file_content, transcoded);
            if (!transcoded.empty()) {
                *file_content = std::move(transcoded);
            }
            else if (utf8_view.size() != file_content->size()) {
                *file_content = std::string{ utf8_view };
            }
            construct_from_utf8_view(*file_content, true);
            return;
        }

        detail::MMapFile mmap{ fs_path };
        std::string transcoded;
        const std::string_view utf8_view = detail::prepare_utf8_view(mmap.view(), transcoded);
        construct_from_utf8_view(utf8_view, true);
    }

    void ConstructFile::construct_from_utf8_view(std::string_view content_view, bool preserve_metadata) {
        struct TransientStateGuard {
            ConstructFile& self;
            ~TransientStateGuard() noexcept {
                self.context_stack_.clear();
                self.active_rules_.clear();
            }
        } state_guard{ *this };

        items.clear();
        if (!preserve_metadata) {
            defines.clear();
        }
        errors.clear();
        last_comment.clear();
        context_stack_.clear();
        context_stack_.emplace_back(this);

        if (detail::ends_with_ci(name, ".str")) {
            StrDocument str_doc = StrParser::parse_file(name, strict, content_view);

            if (!preserve_metadata || delimiters.empty()) {
                std::vector<std::string> str_delims;
                str_delims.reserve(STR_DELIMITERS.size());
                for (const auto kw : STR_DELIMITERS) {
                    str_delims.emplace_back(kw);
                }
                delimiters = { std::move(str_delims), std::vector<std::string>{} };
                start_level = 0;
            }

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

        if (!preserve_metadata || delimiters.empty()) {
            auto [recognized_delims, recognized_start] = recognize_structure_from_utf8(name, content_view);
            delimiters = std::move(recognized_delims);
            if (!preserve_metadata || !delimiters.empty()) {
                start_level = recognized_start;
            }
        }

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
                active_script->end_token = detail::join_views(lexed.words);
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
            std::string ident = detail::join_views(ident_span);
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
            std::string ident = detail::join_views(ident_span);
            validate_sage_bounds(block_name, ident, class_str);

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
            const auto base_lookup_lvl = static_cast<std::size_t>(get_lookup_level());
            for (std::size_t group_idx = 0; group_idx < INI_DELIMITER_RULES.size(); ++group_idx) {
                const auto& group_rules = INI_DELIMITER_RULES[group_idx];
                if (base_lookup_lvl < group_rules.size() &&
                    match_delimiter_rule(lexed.line_tokens, group_rules[base_lookup_lvl]) != nullptr) {
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
        if (remaining_words.size() >= 2 && (detail::ends_with_ci(name, ".ini") || detail::ends_with_ci(name, ".inc"))) {
            block_name = std::string{ remaining_words[0] };
            block_identifier = detail::join_views(remaining_words.subspan(1));
        }
        else if (!remaining_words.empty()) {
            block_name = detail::join_views(remaining_words);
        }

        std::string class_token{ matched_rule->raw };
        const std::size_t next_idx = matched_rule->token_count;
        if (next_idx < line_tokens.size() && line_tokens[next_idx] == "=" && !class_token.ends_with('=')) {
            class_token.append(" =");
        }

        validate_sage_bounds(block_name, block_identifier, class_token);

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

        std::string end_str = detail::join_views(words);
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
            std::string def_text = detail::join_views(words_signs);
            defines.push_back(detail::combine_text_and_comment(def_text, inline_comment));
            append_to_active_context(DefineNode{ std::move(def_text), std::string{ inline_comment } });
            return true;
        }
        if (words[0] == "#include") {
            const std::string raw_path = words_signs.size() > 1
                ? detail::join_views(words_signs.subspan(1))
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
        append_to_active_context(StatementNode{ detail::join_views(words_signs), std::string{ inline_comment } });
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
