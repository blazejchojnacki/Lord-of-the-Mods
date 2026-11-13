/**
 * @file include/ini/parser.hpp
 * @brief Structural parser, iterative serializer, and chroot #include validator for SAGE .ini, .inc, and .str files.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include "ini/lexer.hpp"
#include "ini/schema.hpp"
#include "ini/types.hpp"

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace lotm::ini {

    /**
     * @brief Iteratively serializes a sequence of non-owning node references without call-stack recursion.
     */
    [[nodiscard]] std::string serialize_iterative(
        std::span<const SerializableNodeRef> items,
        int start_level = 0,
        std::string_view file_type = ".ini"
    );

    /**
     * @brief Recognizes the delimiter hierarchy and starting nesting depth of a SAGE .ini, .inc, or .str file.
     */
    [[nodiscard]] std::pair<std::vector<std::vector<std::string>>, int> recognize_structure(
        std::string_view file_path,
        std::optional<std::string_view> file_content = std::nullopt
    );

    /**
     * @brief Validates and resolves a #include directive path strictly within the virtual root jail.
     *
     * @throws IniParseError If the resolved path escapes `virtual_root` or does not exist.
     */
    [[nodiscard]] std::filesystem::path validate_include(
        const IncludeNode& node,
        const std::filesystem::path& current_file,
        const std::filesystem::path& virtual_root
    );

    /**
     * @brief Dedicated single-level parser for SAGE .str localization files.
     */
    class StrParser {
    public:
        [[nodiscard]] static StrDocument parse_file(
            std::string_view file_path,
            bool strict = false,
            std::optional<std::string_view> file_content = std::nullopt
        );
    };

    /**
     * @brief Root AST representation of a fully parsed SAGE .ini, .inc, or .str configuration document.
     */
    class ConstructFile {
    public:
        std::string name{};
        std::string comment{};
        std::vector<std::string> defines{};
        std::vector<std::vector<std::string>> delimiters{};
        int start_level{ 0 };
        bool strict{ false };
        std::optional<std::string> file_content{};

        std::vector<RootItem> items{};
        int current_level{ 0 };
        std::string last_comment{};
        std::vector<std::string> errors{};

        ConstructFile() = default;

        explicit ConstructFile(
            std::string file_name,
            bool is_strict = false,
            std::optional<std::string> content = std::nullopt
        );

        explicit ConstructFile(
            std::string file_name,
            bool is_strict,
            std::span<const uint8_t> buffer
        );

        void construct();

        [[nodiscard]] std::size_t size() const noexcept { return items.size(); }
        [[nodiscard]] bool empty() const noexcept { return items.empty(); }

        void append(RootItem item) { items.push_back(std::move(item)); }
        void append(AstNode item) { items.emplace_back(std::move(item)); }
        void append(StrEntry item) { items.emplace_back(std::move(item)); }

        [[nodiscard]] RootItem& operator[](std::size_t index) { return items[index]; }
        [[nodiscard]] const RootItem& operator[](std::size_t index) const { return items[index]; }

        [[nodiscard]] auto begin() noexcept { return items.begin(); }
        [[nodiscard]] auto end() noexcept { return items.end(); }
        [[nodiscard]] auto begin() const noexcept { return items.begin(); }
        [[nodiscard]] auto end() const noexcept { return items.end(); }
        [[nodiscard]] auto cbegin() const noexcept { return items.cbegin(); }
        [[nodiscard]] auto cend() const noexcept { return items.cend(); }

        [[nodiscard]] std::string print() const;

        [[nodiscard]] bool operator==(const ConstructFile& other) const noexcept {
            return name == other.name &&
                comment == other.comment &&
                defines == other.defines &&
                delimiters == other.delimiters &&
                start_level == other.start_level &&
                strict == other.strict &&
                items == other.items &&
                errors == other.errors;
        }

    private:
        using ContextPtr = std::variant<ConstructFile*, ConstructLevel*, ScriptNode*>;

        std::vector<std::vector<DelimiterRule>> active_rules_{};
        std::vector<ContextPtr> context_stack_{};

        void construct_from_view(std::string_view raw_view);
        [[nodiscard]] int get_lookup_level() const noexcept;
        void append_to_active_context(AstNode node);
        void parse_line(std::string_view raw_line, std::size_t line_num, LexedLine& lex_scratch);
        void handle_empty_line(std::string_view raw_line);
        [[nodiscard]] bool handle_block_start(
            std::span<const std::string_view> words,
            std::span<const std::string_view> line_tokens,
            std::string_view inline_comment
        );
        [[nodiscard]] bool handle_block_end(
            std::span<const std::string_view> words,
            std::size_t line_num,
            std::string_view raw_line,
            std::string_view inline_comment
        );
        [[nodiscard]] bool handle_directives(
            std::span<const std::string_view> words,
            std::span<const std::string_view> words_signs,
            std::string_view inline_comment
        );
        void handle_statement(
            std::span<const std::string_view> words_signs,
            std::string_view inline_comment
        );
    };

    /**
     * @brief Loads and normalizes a structured (.ini, .inc, .str) or raw (.txt) file.
     */
    [[nodiscard]] std::pair<std::string, std::vector<std::vector<std::string>>> load_file(
        std::string_view full_path
    );

    /**
     * @brief Parses a file in non-strict mode and returns any delimiter or level mismatch errors.
     */
    [[nodiscard]] std::vector<std::string> scan_file_for_errors(std::string_view file_path);

} // namespace lotm::ini
