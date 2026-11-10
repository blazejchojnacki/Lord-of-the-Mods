/**
 * @file include/ini/lexer.hpp
 * @brief Zero-copy std::string_view line tokenizer and buffer line iterator for lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <algorithm>
#include <cctype>
#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

namespace lotm::ini {

    /**
     * @brief Zero-copy tokenized representation of a single line from the shared lexer.
     *
     * All token vectors hold non-owning `std::string_view` slices into the source line buffer
     * (or static `"="` / `":"` literals), avoiding per-token heap allocations and separator mutations.
     */
    struct LexedLine {
        std::vector<std::string_view> words{};
        std::vector<std::string_view> words_signs{};
        std::vector<std::string_view> line_tokens{};
        std::string comment{};
    };

    namespace detail {

        [[nodiscard]] constexpr bool is_lex_space(char c) noexcept {
            return c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '\v' || c == '\f';
        }

        [[nodiscard]] constexpr std::string_view lstrip_view(std::string_view sv) noexcept {
            std::size_t pos = 0;
            while (pos < sv.size() && is_lex_space(sv[pos])) {
                ++pos;
            }
            return sv.substr(pos);
        }

        [[nodiscard]] constexpr std::string_view rstrip_view(std::string_view sv) noexcept {
            std::size_t end = sv.size();
            while (end > 0 && is_lex_space(sv[end - 1])) {
                --end;
            }
            return sv.substr(0, end);
        }

        [[nodiscard]] constexpr std::string_view trim_view(std::string_view sv) noexcept {
            return rstrip_view(lstrip_view(sv));
        }

        [[nodiscard]] constexpr bool iequals_ascii(std::string_view a, std::string_view b) noexcept {
            if (a.size() != b.size()) {
                return false;
            }
            for (std::size_t i = 0; i < a.size(); ++i) {
                const char ca = (a[i] >= 'A' && a[i] <= 'Z') ? static_cast<char>(a[i] + ('a' - 'A')) : a[i];
                const char cb = (b[i] >= 'A' && b[i] <= 'Z') ? static_cast<char>(b[i] + ('a' - 'A')) : b[i];
                if (ca != cb) {
                    return false;
                }
            }
            return true;
        }

        [[nodiscard]] inline std::string collapse_whitespace(std::string_view sv) {
            std::string result;
            result.reserve(sv.size());

            std::size_t pos = 0;
            const std::size_t len = sv.size();
            while (pos < len) {
                while (pos < len && is_lex_space(sv[pos])) {
                    ++pos;
                }
                if (pos >= len) {
                    break;
                }
                const std::size_t start = pos;
                while (pos < len && !is_lex_space(sv[pos])) {
                    ++pos;
                }
                if (!result.empty()) {
                    result.push_back(' ');
                }
                result.append(sv.substr(start, pos - start));
            }
            return result;
        }

    } // namespace detail

    /**
     * @brief Populates an existing LexedLine from a raw line view, reusing vector capacities across lines.
     */
    inline void lex_line_into(std::string_view raw_line, LexedLine& out) {
        out.words.clear();
        out.words_signs.clear();
        out.line_tokens.clear();
        out.comment.clear();

        const std::size_t semi_pos = raw_line.find(';');
        const std::size_t slash_pos = raw_line.find("//");
        const std::size_t comment_index = std::min(semi_pos, slash_pos);

        std::string_view code_part = raw_line;
        if (comment_index != std::string_view::npos) {
            code_part = raw_line.substr(0, comment_index);
            out.comment = detail::collapse_whitespace(raw_line.substr(comment_index));
        }

        const std::size_t len = code_part.size();

        // 1. Populate words_signs (whitespace-delimited slices)
        {
            std::size_t pos = 0;
            while (pos < len) {
                while (pos < len && detail::is_lex_space(code_part[pos])) {
                    ++pos;
                }
                if (pos >= len) {
                    break;
                }
                const std::size_t start = pos;
                while (pos < len && !detail::is_lex_space(code_part[pos])) {
                    ++pos;
                }
                out.words_signs.push_back(code_part.substr(start, pos - start));
            }
        }

        // 2. Populate words and line_tokens in a single zero-copy pass without mutating '=' or ':'
        {
            std::size_t pos = 0;
            while (pos < len) {
                while (pos < len && detail::is_lex_space(code_part[pos])) {
                    ++pos;
                }
                if (pos >= len) {
                    break;
                }

                if (code_part[pos] == '=') {
                    out.line_tokens.push_back("=");
                    ++pos;
                }
                else if (code_part[pos] == ':') {
                    out.line_tokens.push_back(":");
                    ++pos;
                }
                else {
                    const std::size_t start = pos;
                    while (pos < len && !detail::is_lex_space(code_part[pos]) &&
                        code_part[pos] != '=' && code_part[pos] != ':') {
                        ++pos;
                    }
                    const std::string_view token = code_part.substr(start, pos - start);
                    out.words.push_back(token);
                    out.line_tokens.push_back(token);
                }
            }
        }
    }

    /**
     * @brief Tokenizes a single line into a LexedLine structure using zero-copy string_view slices.
     */
    [[nodiscard]] inline LexedLine lex_line(std::string_view raw_line) {
        LexedLine result;
        lex_line_into(raw_line, result);
        return result;
    }

    /**
     * @brief Iterates over lines in a contiguous buffer matching Python's `splitlines()` behavior without allocating line strings.
     */
    template <typename Callback>
    inline void for_each_line_view(std::string_view content, Callback&& callback) {
        std::size_t pos = 0;
        std::size_t line_num = 1;
        const std::size_t len = content.size();

        while (pos < len) {
            std::size_t idx = pos;
            while (idx < len && content[idx] != '\n' && content[idx] != '\r') {
                ++idx;
            }

            const std::string_view line = content.substr(pos, idx - pos);
            if constexpr (std::is_invocable_r_v<bool, Callback, std::string_view, std::size_t>) {
                if (!callback(line, line_num)) {
                    return;
                }
            }
            else {
                callback(line, line_num);
            }

            ++line_num;
            if (idx < len) {
                if (content[idx] == '\r' && (idx + 1) < len && content[idx + 1] == '\n') {
                    pos = idx + 2;
                }
                else {
                    pos = idx + 1;
                }
            }
            else {
                pos = len;
            }
        }
    }

} // namespace lotm::ini
