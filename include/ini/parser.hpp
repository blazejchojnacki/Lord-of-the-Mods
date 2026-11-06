/**
 * @file include/ini/parser.hpp
 * @brief Declarations for SAGE .ini, .inc, and .str structural parsers
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <ini/delimiters.hpp>
#include <ini/exceptions.hpp>
#include <ini/types.hpp>

#include <cstddef>
#include <filesystem>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace lotm::ini {

    /**
     * @brief Shared lexer routine extracting comments and tokenizing code segments.
     */
    [[nodiscard]] LexedLine lex_line(std::string_view raw_line);

    /**
     * @brief Formats single-line or multi-line node text with consistent level indentation.
     */
    [[nodiscard]] std::string format_indented_text(std::string_view text, int level);

    /**
     * @brief Pre-sorts and pre-tokenizes delimiter strings to avoid per-line allocations.
     */
    [[nodiscard]] std::vector<DelimiterRule> compile_delimiter_rules(std::span<const std::string> delimiter_list);
    [[nodiscard]] std::vector<DelimiterRule> compile_delimiter_rules(std::span<const std::string_view> delimiter_list);

    /**
     * @brief Matches a tokenized line against pre-compiled delimiter rules without allocation.
     */
    [[nodiscard]] const DelimiterRule* match_delimiter_rule(
        std::span<const std::string> line_tokens,
        std::span<const DelimiterRule> rules
    ) noexcept;

    /**
     * @brief Identifies the active delimiter sets and initial depth level for the given file type.
     */
    [[nodiscard]] std::pair<std::vector<std::vector<std::string>>, int> recognize_structure(
        const std::filesystem::path& file_path
    );

    /**
     * @brief Dedicated single-level parser for SAGE .str localization files.
     */
    class StrParser {
    public:
        [[nodiscard]] static StrDocument parse_file(const std::filesystem::path& file_path, bool strict = false);
    };

    /**
     * @brief The Root representation of a fully parsed SAGE ini/inc/str configuration document.
     */
    class ConstructFile {
    public:
        std::string name{};
        std::vector<std::string> defines{};
        std::vector<std::vector<std::string>> delimiters{};
        int start_level{ 0 };
        bool strict{ false };

        std::vector<AstNode> items{};
        int current_level{ 0 };
        std::string last_comment{};
        std::vector<std::string> errors{};

        ConstructFile() = default;
        explicit ConstructFile(std::filesystem::path file_path, bool strict_mode = false);

        void construct();
        void append(AstNode item);
        [[nodiscard]] std::string print() const;

    private:
        std::filesystem::path file_path_{};
        std::vector<std::vector<DelimiterRule>> active_rules_{};
        std::vector<ConstructLevel*> context_stack_{};

        [[nodiscard]] int get_lookup_level() const noexcept;
        void append_to_active(AstNode item);
        void parse_line(std::string_view raw_line, std::size_t line_num = 0);
        void handle_empty_line(std::string_view raw_line);
        [[nodiscard]] bool handle_block_start(
            std::span<const std::string> words,
            std::span<const std::string> line_tokens
        );
        [[nodiscard]] bool handle_block_end(
            std::span<const std::string> words,
            std::size_t line_num,
            std::string_view raw_line
        );
        [[nodiscard]] bool handle_directives(
            std::span<const std::string> words,
            std::span<const std::string> words_signs
        );
        void handle_statement(
            std::span<const std::string> words_signs,
            std::string inline_comment
        );
    };

    /**
     * @brief Loads a file, parsing it structurally if supported or falling back to raw text.
     */
    [[nodiscard]] std::pair<std::string, std::vector<std::vector<std::string>>> load_file(
        const std::filesystem::path& full_path
    );

    /**
     * @brief Parses a file in non-crashing mode and returns any delimiter or level mismatch errors.
     */
    [[nodiscard]] std::vector<std::string> scan_file_for_errors(
        const std::filesystem::path& file_path
    );

} // namespace lotm::ini
