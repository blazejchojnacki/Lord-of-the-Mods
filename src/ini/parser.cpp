/**
 * @file src/ini/parser.cpp
 * @brief Implementation of SAGE .ini, .inc, and .str structural parsers
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <ini/parser.hpp>

#include <algorithm>
#include <array>
#include <cctype>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace lotm::ini {

    namespace {

        inline std::string to_utf8(const std::filesystem::path& p) {
            auto u8 = p.u8string();
            return std::string(reinterpret_cast<const char*>(u8.data()), u8.size());
        }

        constexpr bool is_ascii_space(char c) noexcept {
            return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\v' || c == '\f';
        }

        std::string_view lstrip_sv(std::string_view sv) noexcept {
            std::size_t i = 0;
            while (i < sv.size() && is_ascii_space(sv[i])) {
                ++i;
            }
            return sv.substr(i);
        }

        bool is_whitespace_only(std::string_view sv) noexcept {
            return lstrip_sv(sv).empty();
        }

        std::vector<std::string> split_whitespace(std::string_view sv) {
            std::vector<std::string> result;
            std::size_t i = 0;
            while (i < sv.size()) {
                while (i < sv.size() && is_ascii_space(sv[i])) {
                    ++i;
                }
                if (i >= sv.size()) {
                    break;
                }
                std::size_t start = i;
                while (i < sv.size() && !is_ascii_space(sv[i])) {
                    ++i;
                }
                result.emplace_back(sv.substr(start, i - start));
            }
            return result;
        }

        std::vector<std::string> split_words_no_punct(std::string_view sv) {
            std::vector<std::string> result;
            std::size_t i = 0;
            while (i < sv.size()) {
                while (i < sv.size() && (is_ascii_space(sv[i]) || sv[i] == '=' || sv[i] == ':')) {
                    ++i;
                }
                if (i >= sv.size()) {
                    break;
                }
                std::size_t start = i;
                while (i < sv.size() && !is_ascii_space(sv[i]) && sv[i] != '=' && sv[i] != ':') {
                    ++i;
                }
                result.emplace_back(sv.substr(start, i - start));
            }
            return result;
        }

        std::vector<std::string> split_line_tokens(std::string_view sv) {
            std::vector<std::string> result;
            std::size_t i = 0;
            while (i < sv.size()) {
                while (i < sv.size() && is_ascii_space(sv[i])) {
                    ++i;
                }
                if (i >= sv.size()) {
                    break;
                }
                if (sv[i] == '=' || sv[i] == ':') {
                    result.emplace_back(1, sv[i]);
                    ++i;
                    continue;
                }
                std::size_t start = i;
                while (i < sv.size() && !is_ascii_space(sv[i]) && sv[i] != '=' && sv[i] != ':') {
                    ++i;
                }
                result.emplace_back(sv.substr(start, i - start));
            }
            return result;
        }

        std::string join_tokens(std::span<const std::string> tokens, std::string_view sep = " ") {
            if (tokens.empty()) {
                return {};
            }
            std::size_t total_len = (tokens.size() - 1) * sep.size();
            for (const auto& t : tokens) {
                total_len += t.size();
            }
            std::string out;
            out.reserve(total_len);
            for (std::size_t i = 0; i < tokens.size(); ++i) {
                if (i > 0) {
                    out.append(sep);
                }
                out.append(tokens[i]);
            }
            return out;
        }

        bool is_valid_utf8(std::string_view data) noexcept {
            const auto* bytes = reinterpret_cast<const uint8_t*>(data.data());
            std::size_t len = data.size();
            std::size_t i = 0;
            while (i < len) {
                uint8_t b0 = bytes[i];
                if (b0 < 0x80) { ++i; }
                else if ((b0 & 0xE0) == 0xC0) {
                    if (b0 < 0xC2 || i + 1 >= len || (bytes[i + 1] & 0xC0) != 0x80) return false;
                    i += 2;
                }
                else if ((b0 & 0xF0) == 0xE0) {
                    if (i + 2 >= len) return false;
                    uint8_t b1 = bytes[i + 1], b2 = bytes[i + 2];
                    if ((b1 & 0xC0) != 0x80 || (b2 & 0xC0) != 0x80) return false;
                    if ((b0 == 0xE0 && b1 < 0xA0) || (b0 == 0xED && b1 >= 0xA0)) return false;
                    i += 3;
                }
                else if ((b0 & 0xF8) == 0xF0) {
                    if (b0 > 0xF4 || i + 3 >= len) return false;
                    uint8_t b1 = bytes[i + 1], b2 = bytes[i + 2], b3 = bytes[i + 3];
                    if ((b1 & 0xC0) != 0x80 || (b2 & 0xC0) != 0x80 || (b3 & 0xC0) != 0x80) return false;
                    if ((b0 == 0xF0 && b1 < 0x90) || (b0 == 0xF4 && b1 >= 0x90)) return false;
                    i += 4;
                }
                else { return false; }
            }
            return true;
        }

        constexpr std::array<uint16_t, 32> CP1252_HIGH_TABLE = {
            0x20AC, 0x0081, 0x201A, 0x0192, 0x201E, 0x2026, 0x2020, 0x2021,
            0x02C6, 0x2030, 0x0160, 0x2039, 0x0152, 0x008D, 0x017D, 0x008F,
            0x0090, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2013, 0x2014,
            0x02DC, 0x2122, 0x0161, 0x203A, 0x0153, 0x009D, 0x017E, 0x0178
        };

        std::string windows1252_to_utf8(std::string_view raw) {
            std::string out;
            out.reserve(raw.size() + raw.size() / 4);
            for (char c : raw) {
                auto uc = static_cast<uint8_t>(c);
                if (uc < 0x80) out.push_back(c);
                else {
                    uint16_t cp = (uc < 0xA0) ? CP1252_HIGH_TABLE[uc - 0x80] : static_cast<uint16_t>(uc);
                    if (cp < 0x800) {
                        out.push_back(static_cast<char>(0xC0 | (cp >> 6)));
                        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
                    }
                    else {
                        out.push_back(static_cast<char>(0xE0 | (cp >> 12)));
                        out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
                        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
                    }
                }
            }
            return out;
        }

        std::string read_file_text(const std::filesystem::path& file_path) {
            std::ifstream in(file_path, std::ios::binary);
            if (!in.is_open()) throw IniParseError("file " + to_utf8(file_path) + " invalid.");
            std::string raw((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
            if (!is_valid_utf8(raw)) raw = windows1252_to_utf8(raw);
            std::string normalized;
            normalized.reserve(raw.size());
            for (std::size_t i = 0; i < raw.size(); ++i) {
                if (raw[i] == '\r') {
                    normalized.push_back('\n');
                    if (i + 1 < raw.size() && raw[i + 1] == '\n') ++i;
                }
                else {
                    normalized.push_back(raw[i]);
                }
            }
            return normalized;
        }

        std::vector<std::string> read_file_lines(const std::filesystem::path& file_path) {
            std::string text = read_file_text(file_path);
            std::vector<std::string> lines;
            std::size_t i = 0;
            while (i < text.size()) {
                std::size_t nl = text.find('\n', i);
                if (nl == std::string::npos) {
                    lines.emplace_back(text.substr(i));
                    break;
                }
                lines.emplace_back(text.substr(i, nl - i));
                i = nl + 1;
            }
            return lines;
        }

        bool is_closing_keyword(std::string_view word) noexcept {
            for (auto end_kw : INI_ENDS) {
                if (word == end_kw) return true;
            }
            return false;
        }

        bool has_supported_extension(std::string_view name) noexcept {
            return name.ends_with(".ini") || name.ends_with(".inc") || name.ends_with(".str");
        }

        const std::vector<std::vector< std::vector<DelimiterRule> >>& get_ini_delimiter_rules() {
            static const auto compiled = []() {
                std::vector<std::vector<std::vector<DelimiterRule>>> result;
                result.reserve(INI_DELIMITERS.size());
                for (const auto& group : INI_DELIMITERS) {
                    std::vector<std::vector<DelimiterRule>> group_rules;
                    group_rules.reserve(group.size());
                    for (const auto& level : group) {
                        group_rules.push_back(compile_delimiter_rules(level));
                    }
                    result.push_back(std::move(group_rules));
                }
                return result;
                }();
            return compiled;
        }

        const std::vector<DelimiterRule>& get_str_delimiter_rules() {
            static const auto compiled = compile_delimiter_rules(
                std::span<const std::string_view>(STR_DELIMITERS)
            );
            return compiled;
        }

        std::vector<std::vector<std::string>> copy_group_delimiters(DelimiterGroup group) {
            std::vector<std::vector<std::string>> delims;
            delims.reserve(group.size() + 1);
            for (const auto& level : group) {
                std::vector<std::string> level_vec;
                level_vec.reserve(level.size());
                for (auto sv : level) level_vec.emplace_back(sv);
                delims.push_back(std::move(level_vec));
            }
            delims.emplace_back();
            return delims;
        }

    } // namespace

    std::string format_indented_text(std::string_view text, int level) {
        const std::size_t indent_count = static_cast<std::size_t>(std::max(0, level));
        std::string indent;
        indent.reserve(indent_count * LEVEL_INDENT.size());
        for (std::size_t i = 0; i < indent_count; ++i) {
            indent.append(LEVEL_INDENT);
        }

        if (text.find('\n') != std::string_view::npos) {
            std::string out;
            std::size_t start = 0;
            while (true) {
                std::size_t nl = text.find('\n', start);
                std::string_view line = (nl == std::string_view::npos)
                    ? text.substr(start)
                    : text.substr(start, nl - start);
                out.append(indent);
                out.append(lstrip_sv(line));
                out.push_back('\n');
                if (nl == std::string_view::npos) break;
                start = nl + 1;
            }
            return out;
        }

        std::string out;
        out.reserve(indent.size() + text.size() + 1);
        out.append(indent);
        out.append(text);
        out.push_back('\n');
        return out;
    }

    std::vector<DelimiterRule> compile_delimiter_rules(std::span<const std::string> delimiter_list) {
        std::vector<DelimiterRule> rules;
        rules.reserve(delimiter_list.size());
        for (const auto& delim : delimiter_list) {
            auto match_tokens = split_line_tokens(delim);
            auto words = split_words_no_punct(delim);
            if (!match_tokens.empty()) {
                rules.push_back(DelimiterRule{ delim, std::move(match_tokens), words.size() });
            }
        }
        std::stable_sort(rules.begin(), rules.end(), [](const DelimiterRule& a, const DelimiterRule& b) {
            return a.match_tokens.size() > b.match_tokens.size();
            });
        return rules;
    }

    std::vector<DelimiterRule> compile_delimiter_rules(std::span<const std::string_view> delimiter_list) {
        std::vector<std::string> copy_list;
        copy_list.reserve(delimiter_list.size());
        for (auto sv : delimiter_list) copy_list.emplace_back(sv);
        return compile_delimiter_rules(std::span<const std::string>(copy_list));
    }

    LexedLine lex_line(std::string_view raw_line) {
        const auto idx_semi = raw_line.find(';');
        const auto idx_slash = raw_line.find("//");

        std::size_t comment_index = std::string_view::npos;
        if (idx_semi != std::string_view::npos && idx_slash != std::string_view::npos) {
            comment_index = std::min(idx_semi, idx_slash);
        }
        else if (idx_semi != std::string_view::npos) {
            comment_index = idx_semi;
        }
        else if (idx_slash != std::string_view::npos) {
            comment_index = idx_slash;
        }

        std::string_view code_part = raw_line;
        std::string comment_text;

        if (comment_index != std::string_view::npos) {
            code_part = raw_line.substr(0, comment_index);
            auto comment_words = split_whitespace(raw_line.substr(comment_index));
            comment_text = join_tokens(comment_words, " ");
        }

        return LexedLine{
            split_words_no_punct(code_part),
            split_whitespace(code_part),
            split_line_tokens(code_part),
            std::move(comment_text)
        };
    }

    const DelimiterRule* match_delimiter_rule(
        std::span<const std::string> line_tokens,
        std::span<const DelimiterRule> rules
    ) noexcept {
        const std::size_t token_count = line_tokens.size();
        for (const auto& rule : rules) {
            const std::size_t k = rule.match_tokens.size();
            if (token_count >= k) {
                bool matches = true;
                for (std::size_t i = 0; i < k; ++i) {
                    if (line_tokens[i] != rule.match_tokens[i]) {
                        matches = false;
                        break;
                    }
                }
                if (matches) return &rule;
            }
        }
        return nullptr;
    }

    std::pair<std::vector<std::vector<std::string>>, int> recognize_structure(
        const std::filesystem::path& file_path
    ) {
        const std::string path_str = to_utf8(file_path);
        if (path_str.ends_with(".str")) {
            std::vector<std::string> str_level;
            str_level.reserve(STR_DELIMITERS.size());
            for (auto sv : STR_DELIMITERS) str_level.emplace_back(sv);
            return { { std::move(str_level),{} }, 0 };
        }
        if (path_str.ends_with(".ini") || path_str.ends_with(".inc")) {
            const bool is_ini = path_str.ends_with(".ini");
            const auto& ini_rules = get_ini_delimiter_rules();
            const auto lines = read_file_lines(file_path);

            for (const auto& file_line : lines) {
                auto lexed = lex_line(file_line);
                if (lexed.line_tokens.empty()) continue;

                for (std::size_t group_idx = 0; group_idx < ini_rules.size(); ++group_idx) {
                    const auto& group_rules = ini_rules[group_idx];
                    for (std::size_t level_idx = 0; level_idx < group_rules.size(); ++level_idx) {
                        if (is_ini && level_idx > 0) break;
                        if (match_delimiter_rule(lexed.line_tokens, group_rules[level_idx]) != nullptr) {
                            return {
                                copy_group_delimiters(INI_DELIMITERS[group_idx]),
                                static_cast<int>(level_idx)
                            };
                        }
                    }
                }
            }
        }
        return { {}, 0 };
    }

    std::string StrEntry::print() const {
        std::string output;

        if (!identifier.empty()) {
            output.append(category);
            output.push_back(':');
            output.append(identifier);
        }
        else {
            output.append(category);
        }
        output.push_back('\n');

        for (const auto& item : items) {
            std::visit([&output](const auto& node) {
                using T = std::decay_t<decltype(node)>;
                if constexpr (std::is_same_v<T, StatementNode>) {
                    std::string combined = node.text;
                    if (!node.comment.empty()) {
                        combined.append(" ");
                        combined.append(node.comment);
                    }
                    output.append(format_indented_text(combined, 1));
                }
                else {
                    output.append(format_indented_text(node.text, 1));
                }
                }, item);
        }

        if (!end_token.empty()) {
            output.append(end_token);
            output.push_back('\n');
        }
        return output;
    }

    std::string StrDocument::print() const {
        std::string output;
        for (const auto& entry : entries) {
            std::visit([&output](const auto& node) {
                using T = std::decay_t<decltype(node)>;
                if constexpr (std::is_same_v<T, StrEntry>) {
                    output.append(node.print());
                }
                else if constexpr (std::is_same_v<T, StatementNode>) {
                    std::string combined = node.text;
                    if (!node.comment.empty()) {
                        combined.append(" ");
                        combined.append(node.comment);
                    }
                    output.append(format_indented_text(combined, 0));
                }
                else {
                    output.append(format_indented_text(node.text, 0));
                }
                }, entry);
            output.push_back('\n');
        }
        return output;
    }

    StrDocument StrParser::parse_file(const std::filesystem::path& file_path, bool strict) {
        const std::string path_str = to_utf8(file_path);
        if (!std::filesystem::is_regular_file(file_path) || !path_str.ends_with(".str")) {
            throw IniParseError("file " + path_str + " invalid.");
        }

        StrDocument doc{ path_str,{},{} };
        StrEntry active_entry{};
        bool has_active_entry = false;
        std::string last_comment;

        const auto& str_rules = get_str_delimiter_rules();
        const auto lines = read_file_lines(file_path);

        for (std::size_t idx = 0; idx < lines.size(); ++idx) {
            const std::size_t line_num = idx + 1;
            const std::string& raw_line = lines[idx];
            auto lexed = lex_line(raw_line);

            // Empty line or purely standalone comment line
            if (lexed.words.empty()) {
                if (!lexed.comment.empty()) {
                    if (!last_comment.empty()) last_comment.push_back('\n');
                    last_comment.append(lexed.comment);
                }
                if (!last_comment.empty() && is_whitespace_only(raw_line)) {
                    if (has_active_entry) active_entry.items.emplace_back(CommentNode{ last_comment });
                    else doc.entries.emplace_back(CommentNode{ last_comment });
                    last_comment.clear();
                }
                continue;
            }

            // We reached a block or statement. Flush any preceding multi-line block comments.
            if (!last_comment.empty()) {
                if (has_active_entry) active_entry.items.emplace_back(CommentNode{ last_comment });
                else doc.entries.emplace_back(CommentNode{ last_comment });
                last_comment.clear();
            }

            if (!has_active_entry) {
                const DelimiterRule* matched_rule = match_delimiter_rule(lexed.line_tokens, str_rules);
                if (matched_rule != nullptr) {
                    std::span<const std::string> remaining(lexed.words);
                    remaining = remaining.subspan(std::min(matched_rule->word_count, remaining.size()));

                    // If the header line itself has an inline comment, it becomes a StatementNode item inside
                    // the block to preserve it on the same line, or we append it as a CommentNode inside.
                    active_entry = StrEntry{
                        matched_rule->raw,
                        join_tokens(remaining, " "),
                        "End",
                        {}
                    };
                    has_active_entry = true;
                    if (!lexed.comment.empty()) {
                        active_entry.items.emplace_back(StatementNode{ "", lexed.comment });
                    }
                    continue;
                }
            }

            if (is_closing_keyword(lexed.words[0])) {
                if (!has_active_entry) {
                    std::string err_msg = "Delimiter mismatch: negative level reached at " +
                        path_str + ":" + std::to_string(line_num) +
                        " on closing keyword '" + lexed.words[0] + "': " +
                        std::string(lstrip_sv(raw_line));
                    doc.errors.push_back(err_msg);
                    if (strict) throw IniParseError(err_msg);

                    doc.entries.emplace_back(StatementNode{ join_tokens(lexed.words, " "), lexed.comment });
                }
                else {
                    active_entry.end_token = join_tokens(lexed.words, " ");
                    // If the end line has an inline comment, store it. In SAGE, usually appended to the end token line natively
                    // but StrEntry doesn't have an end_comment field. Appending to items forces it just before the END.
                    if (!lexed.comment.empty()) {
                        active_entry.items.emplace_back(StatementNode{ "", lexed.comment });
                    }
                    doc.entries.emplace_back(std::move(active_entry));
                    active_entry = StrEntry{};
                    has_active_entry = false;
                }
                continue;
            }

            // Statement with inline comment
            StatementNode stmt{ join_tokens(lexed.words_signs, " "), lexed.comment };
            if (has_active_entry) {
                active_entry.items.emplace_back(std::move(stmt));
            }
            else {
                doc.entries.emplace_back(std::move(stmt));
            }
        }

        if (has_active_entry) {
            doc.entries.emplace_back(std::move(active_entry));
        }

        return doc;
    }

    void ConstructLevel::append(AstNode item) {
        items.push_back(std::move(item));
    }

    std::string ConstructLevel::print(int level, std::string_view file_type) const {
        const std::size_t indent_count = static_cast<std::size_t>(std::max(0, level));
        std::string indent;
        indent.reserve(indent_count * LEVEL_INDENT.size());
        for (std::size_t i = 0; i < indent_count; ++i) {
            indent.append(LEVEL_INDENT);
        }

        std::string output;

        const std::string_view sep = (file_type == ".ini" || file_type == ".inc") ? " " : ":";
        std::vector<std::string> header_parts;
        if (!_class.empty()) header_parts.push_back(_class);
        if (!name.empty()) header_parts.push_back(name);
        if (!identifier.empty()) header_parts.push_back(identifier);

        if (!header_parts.empty()) {
            std::string joined = join_tokens(header_parts, sep);
            output.append(format_indented_text(lstrip_sv(joined), level));
        }

        const int inner_level = level + 1;
        for (const auto& item : items) {
            std::visit([&output, inner_level, file_type](const auto& node) {
                using T = std::decay_t<decltype(node)>;
                if constexpr (std::is_same_v<T, ConstructLevel>) {
                    output.append(node.print(inner_level, file_type));
                }
                else if constexpr (std::is_same_v<T, StrEntry>) {
                    output.append(node.print());
                }
                else if constexpr (std::is_same_v<T, StatementNode>) {
                    std::string combined = node.text;
                    if (!node.comment.empty()) {
                        if (!combined.empty()) combined.append(" ");
                        combined.append(node.comment);
                    }
                    output.append(format_indented_text(combined, inner_level));
                }
                else {
                    output.append(format_indented_text(node.text, inner_level));
                }
                }, item.value);
        }

        if (!end_token.empty()) {
            output.append(indent);
            output.append(end_token);
            output.push_back('\n');
        }

        return output;
    }

    ConstructFile::ConstructFile(std::filesystem::path file_path, bool strict_mode)
        : name(to_utf8(file_path)),
        strict(strict_mode),
        file_path_(std::move(file_path)) {
        if (!name.empty()) {
            construct();
        }
    }

    void ConstructFile::append(AstNode item) {
        items.push_back(std::move(item));
    }

    void ConstructFile::append_to_active(AstNode item) {
        if (context_stack_.empty()) {
            items.push_back(std::move(item));
        }
        else {
            context_stack_.back()->items.push_back(std::move(item));
        }
    }

    void ConstructFile::construct() {
        if (file_path_.empty() && !name.empty()) {
            file_path_ = std::filesystem::path(
                std::u8string_view(reinterpret_cast<const char8_t*>(name.data()), name.size())
            );
        }
        else if (!file_path_.empty()) {
            name = to_utf8(file_path_);
        }

        if (!std::filesystem::is_regular_file(file_path_) || !has_supported_extension(name)) {
            throw IniParseError("file " + name + " invalid.");
        }

        items.clear();
        defines.clear();
        errors.clear();
        last_comment.clear();
        context_stack_.clear();

        if (name.ends_with(".str")) {
            auto str_doc = StrParser::parse_file(file_path_, strict);
            std::vector<std::string> str_level;
            str_level.reserve(STR_DELIMITERS.size());
            for (auto sv : STR_DELIMITERS) str_level.emplace_back(sv);
            delimiters = { std::move(str_level),{} };
            start_level = 0;
            for (auto& entry : str_doc.entries) {
                std::visit([this](auto&& node) {
                    items.emplace_back(std::forward<decltype(node)>(node));
                    }, std::move(entry));
            }
            errors = std::move(str_doc.errors);
            return;
        }

        auto [rec_delims, rec_start] = recognize_structure(file_path_);
        delimiters = std::move(rec_delims);
        start_level = rec_start;
        current_level = start_level;

        active_rules_.clear();
        active_rules_.reserve(delimiters.size());
        for (const auto& level : delimiters) {
            active_rules_.push_back(compile_delimiter_rules(level));
        }

        const auto lines = read_file_lines(file_path_);
        for (std::size_t idx = 0; idx < lines.size(); ++idx) {
            parse_line(lines[idx], idx + 1);
        }
    }

    int ConstructFile::get_lookup_level() const noexcept {
        int shift = 0;
        for (const auto* blk : context_stack_) {
            if (blk->_class == "ReplaceModule") {
                ++shift;
            }
        }
        return std::max(0, current_level - shift);
    }

    void ConstructFile::parse_line(std::string_view raw_line, std::size_t line_num) {
        auto lexed = lex_line(raw_line);

        // Handle pure empty lines or standalone comments
        if (lexed.words.empty()) {
            if (!lexed.comment.empty()) {
                if (!last_comment.empty()) last_comment.push_back('\n');
                last_comment.append(lexed.comment);
            }
            if (!last_comment.empty() && is_whitespace_only(raw_line)) {
                append_to_active(CommentNode{ last_comment });
                last_comment.clear();
            }
            return;
        }

        // We reached a block or statement. Flush any preceding block-level comments as standalone nodes.
        if (!last_comment.empty()) {
            append_to_active(CommentNode{ last_comment });
            last_comment.clear();
        }

        if (handle_block_start(lexed.words, lexed.line_tokens)) {
            // If the block declaration header line has an inline comment, append it to the block as a statement node inside
            // (or if we had a dedicated end_comment field we could use it, but keeping it as a statement node works).
            if (!lexed.comment.empty()) {
                append_to_active(StatementNode{ "", lexed.comment });
            }
            return;
        }

        if (handle_block_end(lexed.words, line_num, raw_line)) {
            // Appending an empty statement with a comment forces it inside the parent scope just before the end_token.
            if (!lexed.comment.empty()) {
                append_to_active(StatementNode{ "", lexed.comment });
            }
            return;
        }

        if (handle_directives(lexed.words, lexed.words_signs)) {
            if (!lexed.comment.empty()) {
                append_to_active(StatementNode{ "", lexed.comment });
            }
            return;
        }

        if (current_level == start_level) {
            const auto& ini_rules = get_ini_delimiter_rules();
            for (std::size_t group_idx = 0; group_idx < ini_rules.size(); ++group_idx) {
                const auto& group_rules = ini_rules[group_idx];
                if (!group_rules.empty()) {
                    if (match_delimiter_rule(lexed.line_tokens, group_rules[0]) != nullptr) {
                        delimiters = copy_group_delimiters(INI_DELIMITERS[group_idx]);
                        active_rules_ = group_rules;
                        active_rules_.emplace_back();
                        if (handle_block_start(lexed.words, lexed.line_tokens)) {
                            if (!lexed.comment.empty()) {
                                append_to_active(StatementNode{ "", lexed.comment });
                            }
                            return;
                        }
                    }
                }
            }
        }

        handle_statement(lexed.words_signs, lexed.comment);
    }

    void ConstructFile::handle_empty_line(std::string_view raw_line) {
        if (!last_comment.empty() && is_whitespace_only(raw_line)) {
            append_to_active(CommentNode{ last_comment });
            last_comment.clear();
        }
    }

    bool ConstructFile::handle_block_start(
        std::span<const std::string> words,
        std::span<const std::string> line_tokens
    ) {
        const auto lookup_level = static_cast<std::size_t>(get_lookup_level());
        if (lookup_level < active_rules_.size()) {
            const DelimiterRule* matched_rule = match_delimiter_rule(line_tokens, active_rules_[lookup_level]);
            if (matched_rule != nullptr) {
                auto remaining_words = words.subspan(std::min(matched_rule->word_count, words.size()));

                const bool is_sage_config = name.ends_with(".ini") || name.ends_with(".inc");
                std::string block_name;
                std::string block_identifier;
                if (remaining_words.size() == 2 && is_sage_config) {
                    block_name = remaining_words[0];
                    block_identifier = remaining_words[1];
                }
                else if (!remaining_words.empty()) {
                    block_name = join_tokens(remaining_words, " ");
                }

                std::string class_token = matched_rule->raw;
                const std::size_t next_idx = matched_rule->match_tokens.size();
                if (next_idx < line_tokens.size() && line_tokens[next_idx] == "=" && !class_token.ends_with("=")) {
                    class_token.append(" =");
                }

                ConstructLevel new_block(
                    std::move(class_token),
                    std::move(block_name),
                    std::move(block_identifier)
                );

                if (context_stack_.empty()) {
                    items.emplace_back(std::move(new_block));
                    context_stack_.push_back(&std::get<ConstructLevel>(items.back().value));
                }
                else {
                    auto& parent_items = context_stack_.back()->items;
                    parent_items.emplace_back(std::move(new_block));
                    context_stack_.push_back(&std::get<ConstructLevel>(parent_items.back().value));
                }

                ++current_level;
                return true;
            }
        }
        return false;
    }

    bool ConstructFile::handle_block_end(
        std::span<const std::string> words,
        std::size_t line_num,
        std::string_view raw_line
    ) {
        if (is_closing_keyword(words[0])) {
            --current_level;
            if (current_level < 0) {
                std::string err_msg = "Delimiter mismatch: negative level reached at " +
                    name + ":" + std::to_string(line_num) +
                    " on closing keyword '" + words[0] + "': " +
                    std::string(lstrip_sv(raw_line));
                errors.push_back(err_msg);
                if (strict) {
                    throw IniParseError(err_msg);
                }
                current_level = 0;
            }

            std::string end_str = join_tokens(words, " ");
            if (!context_stack_.empty()) {
                context_stack_.back()->end_token = std::move(end_str);
                context_stack_.pop_back();
            }
            else {
                append_to_active(StatementNode{ std::move(end_str) });
            }
            return true;
        }
        return false;
    }

    bool ConstructFile::handle_directives(
        std::span<const std::string> words,
        std::span<const std::string> words_signs
    ) {
        if (words[0] == "#define") {
            defines.push_back(join_tokens(words_signs, " "));
            return true;
        }
        if (words[0] == "#include") {
            append_to_active(IncludeNode{ join_tokens(words_signs, " ") });
            return true;
        }
        return false;
    }

    void ConstructFile::handle_statement(
        std::span<const std::string> words_signs,
        std::string inline_comment
    ) {
        append_to_active(StatementNode{ join_tokens(words_signs, " "), std::move(inline_comment) });
    }

    std::string ConstructFile::print() const {
        std::string output;
        for (const auto& line : defines) {
            output.append(line);
            output.push_back('\n');
        }

        const std::string_view file_type = (name.size() >= 4)
            ? std::string_view(name).substr(name.size() - 4)
            : std::string_view(".ini");

        for (const auto& item : items) {
            std::visit([this, &output, file_type](const auto& node) {
                using T = std::decay_t<decltype(node)>;
                if constexpr (std::is_same_v<T, StrEntry>) {
                    output.append(node.print());
                }
                else if constexpr (std::is_same_v<T, ConstructLevel>) {
                    output.append(node.print(start_level, file_type));
                }
                else if constexpr (std::is_same_v<T, StatementNode>) {
                    std::string combined = node.text;
                    if (!node.comment.empty()) {
                        if (!combined.empty()) combined.append(" ");
                        combined.append(node.comment);
                    }
                    output.append(format_indented_text(combined, start_level));
                }
                else {
                    output.append(format_indented_text(node.text, start_level));
                }
                }, item.value);
            output.push_back('\n');
        }
        return output;
    }

    std::pair<std::string, std::vector<std::vector<std::string>>> load_file(
        const std::filesystem::path& full_path
    ) {
        if (full_path.empty()) {
            throw IniParseError("empty path.");
        }
        const std::string path_str = to_utf8(full_path);
        if (!std::filesystem::is_regular_file(full_path)) {
            throw IniParseError("wrong path: " + path_str);
        }

        if (has_supported_extension(path_str)) {
            try {
                ConstructFile file_object(full_path, false);
                std::string file_content = file_object.print();
                if (file_content.empty()) {
                    return { read_file_text(full_path),{} };
                }
                return { std::move(file_content), std::move(file_object.delimiters) };
            }
            catch (const IniParseError&) {
                return { read_file_text(full_path),{} };
            }
        }
        if (path_str.ends_with(".txt")) {
            return { read_file_text(full_path),{} };
        }

        throw IniParseError("wrong path or unsupported file type: " + path_str);
    }

    std::vector<std::string> scan_file_for_errors(const std::filesystem::path& file_path) {
        try {
            ConstructFile file_object(file_path, false);
            return file_object.errors;
        }
        catch (const std::exception& exc) {
            return { "Fatal error while processing " + to_utf8(file_path) + ": " + exc.what() };
        }
    }

} // namespace lotm::ini
