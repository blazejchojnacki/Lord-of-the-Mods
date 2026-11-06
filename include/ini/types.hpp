/**
 * @file include/ini/types.hpp
 * @brief AST node structures and lexer types for SAGE configuration files
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <array>
#include <concepts>
#include <cstddef>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

namespace lotm::ini {

    inline constexpr std::string_view LEVEL_INDENT = "    ";
    inline constexpr std::array<std::string_view, 3> INI_ENDS = { "End", "END", "EndScript" };

    /**
     * @brief Pre-tokenized delimiter rule isomorphic to the Python prototype.
     */
    struct DelimiterRule {
        std::string raw;
        std::vector<std::string> match_tokens;
        std::size_t word_count{ 0 };
    };

    /**
     * @brief Tokenized representation of a single line from the shared lexer.
     */
    struct LexedLine {
        std::vector<std::string> words;
        std::vector<std::string> words_signs;
        std::vector<std::string> line_tokens;
        std::string comment;
    };

    /**
     * @brief Represents a standalone or block-internal comment.
     */
    struct CommentNode {
        std::string text;
    };

    /**
     * @brief Represents a standard property assignment or value line.
     */
    struct StatementNode {
        std::string text;
        std::string comment;
    };

    /**
     * @brief Represents a #include preprocessor directive.
     */
    struct IncludeNode {
        std::string text;
    };

    using StrItem = std::variant<CommentNode, StatementNode>;

    /**
     * @brief Represents a single localized string entry inside a SAGE .str file.
     */
    struct StrEntry {
        std::string category;
        std::string identifier;
        std::string comment{};
        std::string end_token{ "End" };
        std::vector<StrItem> items{};

        [[nodiscard]] std::string print() const;
    };

    using StrDocEntry = std::variant<StrEntry, CommentNode, StatementNode>;

    /**
     * @brief Flat AST representation for SAGE .str localization files.
     */
    struct StrDocument {
        std::string name;
        std::vector<StrDocEntry> entries{};
        std::vector<std::string> errors{};

        [[nodiscard]] std::string print() const;
    };

    struct AstNode;

    /**
     * @brief Represents an inner block or defined object within a parsed SAGE configuration file.
     */
    struct ConstructLevel {
        std::string _class{};
        std::string name{};
        std::string identifier{};
        std::string comment{};
        std::string end_token{};
        std::vector<AstNode> items{};

        ConstructLevel() = default;
        ConstructLevel(
            std::string cls,
            std::string blk_name = "",
            std::string blk_id = "",
            std::string blk_comment = "",
            std::string blk_end = ""
        );
        ~ConstructLevel();
        ConstructLevel(const ConstructLevel&);
        ConstructLevel(ConstructLevel&&) noexcept;
        ConstructLevel& operator=(const ConstructLevel&);
        ConstructLevel& operator=(ConstructLevel&&) noexcept;

        void append(AstNode item);
        [[nodiscard]] std::string print(int level = 0, std::string_view file_type = ".ini") const;
    };

    using AstNodeVariant = std::variant<CommentNode, StatementNode, IncludeNode, ConstructLevel, StrEntry>;

    /**
     * @brief Recursive variant wrapper representing any AST node inside a block or document.
     */
    struct AstNode {
        AstNodeVariant value;

        template <typename T>
            requires (!std::same_as<std::remove_cvref_t<T>, AstNode>&&
        std::constructible_from<AstNodeVariant, T>)
            AstNode(T&& v) : value(std::forward<T>(v)) {}
    };

    inline ConstructLevel::ConstructLevel(
        std::string cls,
        std::string blk_name,
        std::string blk_id,
        std::string blk_comment,
        std::string blk_end
    )
        : _class(std::move(cls)),
        name(std::move(blk_name)),
        identifier(std::move(blk_id)),
        comment(std::move(blk_comment)),
        end_token(std::move(blk_end)) {
    }

    inline ConstructLevel::~ConstructLevel() = default;
    inline ConstructLevel::ConstructLevel(const ConstructLevel&) = default;
    inline ConstructLevel::ConstructLevel(ConstructLevel&&) noexcept = default;
    inline ConstructLevel& ConstructLevel::operator=(const ConstructLevel&) = default;
    inline ConstructLevel& ConstructLevel::operator=(ConstructLevel&&) noexcept = default;

} // namespace lotm::ini
