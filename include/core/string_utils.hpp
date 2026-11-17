/**
 * @file include/core/string_utils.hpp
 * @brief Locale-independent constexpr ASCII character and string_view manipulation utilities.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <cstddef>
#include <string>
#include <string_view>

namespace lotm::core {

    /**
     * @brief Checks whether a character is standard ASCII whitespace.
     */
    [[nodiscard]] constexpr bool is_ascii_space(char c) noexcept {
        return c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '\v' || c == '\f';
    }

    /**
     * @brief Checks whether a character is an ASCII alphabetic letter ('A'-'Z' or 'a'-'z').
     */
    [[nodiscard]] constexpr bool is_ascii_alpha(char c) noexcept {
        return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
    }

    /**
     * @brief Converts an ASCII uppercase character to lowercase without locale dependency.
     */
    [[nodiscard]] constexpr char to_lower_ascii_char(char c) noexcept {
        return (c >= 'A' && c <= 'Z') ? static_cast<char>(c + ('a' - 'A')) : c;
    }

    /**
     * @brief Converts an ASCII lowercase character to uppercase without locale dependency.
     */
    [[nodiscard]] constexpr char to_upper_ascii_char(char c) noexcept {
        return (c >= 'a' && c <= 'z') ? static_cast<char>(c - ('a' - 'A')) : c;
    }

    /**
     * @brief Strips leading ASCII whitespace from a string_view without allocation.
     */
    [[nodiscard]] constexpr std::string_view lstrip_view(std::string_view sv) noexcept {
        std::size_t pos = 0;
        while (pos < sv.size() && is_ascii_space(sv[pos])) {
            ++pos;
        }
        return sv.substr(pos);
    }

    /**
     * @brief Strips trailing ASCII whitespace from a string_view without allocation.
     */
    [[nodiscard]] constexpr std::string_view rstrip_view(std::string_view sv) noexcept {
        std::size_t end = sv.size();
        while (end > 0 && is_ascii_space(sv[end - 1])) {
            --end;
        }
        return sv.substr(0, end);
    }

    /**
     * @brief Strips both leading and trailing ASCII whitespace from a string_view.
     */
    [[nodiscard]] constexpr std::string_view trim_view(std::string_view sv) noexcept {
        return rstrip_view(lstrip_view(sv));
    }

    /**
     * @brief Compares two string_views for case-insensitive ASCII equality.
     */
    [[nodiscard]] constexpr bool iequals_ascii(std::string_view a, std::string_view b) noexcept {
        if (a.size() != b.size()) {
            return false;
        }
        for (std::size_t i = 0; i < a.size(); ++i) {
            if (to_lower_ascii_char(a[i]) != to_lower_ascii_char(b[i])) {
                return false;
            }
        }
        return true;
    }

    /**
     * @brief Checks whether a string_view ends with the given suffix case-insensitively.
     */
    [[nodiscard]] constexpr bool ends_with_ci(std::string_view str, std::string_view suffix) noexcept {
        if (str.size() < suffix.size()) {
            return false;
        }
        return iequals_ascii(str.substr(str.size() - suffix.size()), suffix);
    }

    /**
     * @brief Returns a lowercase ASCII copy of the input string_view.
     */
    [[nodiscard]] inline std::string to_lower_ascii(std::string_view sv) {
        std::string result(sv);
        for (char& c : result) {
            c = to_lower_ascii_char(c);
        }
        return result;
    }

} // namespace lotm::core
