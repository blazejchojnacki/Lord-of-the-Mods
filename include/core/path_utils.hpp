/**
 * @file include/core/path_utils.hpp
 * @brief Shared UTF-8 path conversion, glob matching, and Windows NTFS/device security validation helpers.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <core/string_utils.hpp>
#include <cstddef>
#include <filesystem>
#include <string>
#include <string_view>

namespace lotm::core {

    /**
     * @brief Converts a std::filesystem::path to a UTF-8 std::string without using Windows CP_ACP.
     */
    [[nodiscard]] inline std::string to_utf8(const std::filesystem::path& p) {
        const auto u8 = p.u8string();
        return std::string(reinterpret_cast<const char*>(u8.data()), u8.size());
    }

    /**
     * @brief Constructs a std::filesystem::path from a UTF-8 std::string_view without using Windows CP_ACP.
     */
    [[nodiscard]] inline std::filesystem::path utf8_to_path(std::string_view utf8_str) {
        const std::u8string_view u8_view(
            reinterpret_cast<const char8_t*>(utf8_str.data()),
            utf8_str.size()
        );
        return std::filesystem::path(u8_view);
    }

    /**
     * @brief Normalizes a virtual archive entry path to lowercase ASCII with platform-preferred separators.
     */
    [[nodiscard]] inline std::string normalize_virtual_path(std::string_view entry_name) {
        std::string key(entry_name);
        for (char& c : key) {
            if (c == '\\' || c == '/') {
                c = static_cast<char>(std::filesystem::path::preferred_separator);
            }
            else {
                c = to_lower_ascii_char(c);
            }
        }
        return key;
    }

    // Case-insensitive glob matcher supporting '*' and '?' with normalized path separators
    [[nodiscard]] inline bool matches_glob(std::string_view text, std::string_view pattern) noexcept {
        if (pattern.empty() || pattern == "*") {
            return true;
        }

        auto norm = [](char c) noexcept -> char {
            if (c == '\\' || c == '/') {
                return static_cast<char>(std::filesystem::path::preferred_separator);
            }
            return to_lower_ascii_char(c);
            };

        std::size_t t_idx = 0;
        std::size_t p_idx = 0;
        std::size_t star_idx = std::string_view::npos;
        std::size_t match_idx = 0;

        while (t_idx < text.size()) {
            if (p_idx < pattern.size() && (pattern[p_idx] == '?' || norm(pattern[p_idx]) == norm(text[t_idx]))) {
                ++t_idx;
                ++p_idx;
            }
            else if (p_idx < pattern.size() && pattern[p_idx] == '*') {
                star_idx = p_idx;
                match_idx = t_idx;
                ++p_idx;
            }
            else if (star_idx != std::string_view::npos) {
                p_idx = star_idx + 1;
                ++match_idx;
                t_idx = match_idx;
            }
            else {
                return false;
            }
        }

        while (p_idx < pattern.size() && pattern[p_idx] == '*') {
            ++p_idx;
        }

        return p_idx == pattern.size();
    }

    // Checks for extended Win32 and NT namespace prefixes (\\?, \\., \?, \., \??)
    [[nodiscard]] inline bool has_win32_namespace_prefix(std::string_view path) noexcept {
        constexpr char sep = static_cast<char>(std::filesystem::path::preferred_separator);
        std::size_t pos = 0;
        while (pos < path.size() && path[pos] == sep) {
            ++pos;
        }
        return pos > 0 && pos < path.size() && (path[pos] == '?' || path[pos] == '.');
    }

    // Checks for Windows drive-relative paths (e.g., C:file.txt, D:..\escaped.txt)
    [[nodiscard]] inline bool is_drive_relative_path(std::string_view path) noexcept {
        constexpr char sep = static_cast<char>(std::filesystem::path::preferred_separator);
        return path.size() >= 2 &&
            is_ascii_alpha(path[0]) &&
            path[1] == ':' &&
            (path.size() == 2 || path[2] != sep);
    }

    // Checks for Windows reserved device names and Alternate Data Streams (ADS)
    [[nodiscard]] inline bool is_unsafe_ntfs_component(std::string_view name) {
        if (name.empty() || name == "." || name == ".." ||
            name.back() == ' ' || name.back() == '.') {
            return true;
        }

        std::string upper_name;
        upper_name.reserve(name.size());
        for (char c : name) {
            const auto uc = static_cast<unsigned char>(c);
            if (uc < 32 || c == ':' || c == '<' || c == '>' ||
                c == '"' || c == '|' || c == '?' || c == '*') {
                return true;
            }
            upper_name.push_back(to_upper_ascii_char(c));
        }

        auto dot_pos = upper_name.find('.');
        std::string_view base = (dot_pos != std::string_view::npos)
            ? std::string_view(upper_name).substr(0, dot_pos)
            : upper_name;

        // Strip trailing spaces and dots (Win32 path normalization trims them before device check)
        while (!base.empty() && (base.back() == ' ' || base.back() == '.')) {
            base.remove_suffix(1);
        }

        if (base == "CON" || base == "PRN" || base == "AUX" || base == "NUL" ||
            base == "CONIN$" || base == "CONOUT$" || base == "CLOCK$") {
            return true;
        }
        if (base.starts_with("COM") || base.starts_with("LPT")) {
            if (base.size() == 4) {
                const auto digit = static_cast<unsigned char>(base[3]);
                if ((digit >= '0' && digit <= '9') ||
                    digit == 0xB9 || digit == 0xB2 || digit == 0xB3) {
                    return true;
                }
            }
            else if (base.size() == 5 && static_cast<unsigned char>(base[3]) == 0xC2) {
                const auto sup = static_cast<unsigned char>(base[4]);
                if (sup == 0xB9 || sup == 0xB2 || sup == 0xB3) {
                    return true;
                }
            }
        }
        return false;
    }

} // namespace lotm::core
