/**
 * @file src/ini/parser_utils.hpp
 * @brief Internal shared utilities, I/O wrappers, and string helpers for INI parser components.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <filesystem>
#include <span>
#include <string>
#include <string_view>

namespace lotm::ini::detail {

    /**
     * @brief Case-insensitive suffix check.
     */
    [[nodiscard]] bool ends_with_ci(std::string_view str, std::string_view suffix) noexcept;

    /**
     * @brief Validates if a file extension is recognized (.ini, .inc, .str).
     */
    [[nodiscard]] bool is_supported_config_ext(std::string_view path) noexcept;

    /**
     * @brief Joins a span of string_views into a single string separated by `sep`.
     */
    [[nodiscard]] std::string join_views(std::span<const std::string_view> tokens, std::string_view sep = " ");

    /**
     * @brief Combines a text value and an inline comment with proper spacing.
     */
    [[nodiscard]] std::string combine_text_and_comment(std::string_view text, std::string_view comment);

    /**
     * @brief Ensures a raw file view is valid UTF-8, transcoding legacy Windows-1252 if necessary.
     */
    [[nodiscard]] std::string_view prepare_utf8_view(
        std::string_view raw_view,
        std::string& transcoded_storage
    );

    /**
     * @brief RAII Memory Mapped File for zero-copy file reading.
     *        Utilizes opaque pointers to prevent leaking <windows.h> into internal implementation files.
     */
    class MMapFile {
    public:
        explicit MMapFile(const std::filesystem::path& path);
        ~MMapFile();

        MMapFile(const MMapFile&) = delete;
        MMapFile& operator=(const MMapFile&) = delete;

        MMapFile(MMapFile&& other) noexcept;
        MMapFile& operator=(MMapFile&& other) noexcept;

        [[nodiscard]] std::string_view view() const noexcept {
            return { data_ ? data_ : "", size_ };
        }

    private:
        std::size_t size_{ 0 };
        const char* data_{ nullptr };
        void* file_handle_{ nullptr };
        void* map_handle_{ nullptr };
    };

} // namespace lotm::ini::detail
