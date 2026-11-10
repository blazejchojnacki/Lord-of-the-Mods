/**
 * @file include/ini/types.hpp
 * @brief AST node definitions, variants, and iterative serialization frame structures for lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace lotm::ini {

    /**
     * @brief Domain-specific exception thrown on structural INI/INC/STR parsing or security violations.
     */
    class IniParseError : public std::runtime_error {
    public:
        using std::runtime_error::runtime_error;
    };

    inline constexpr std::string_view LEVEL_INDENT = "    ";
    inline constexpr std::array<std::string_view, 3> INI_ENDS = { "End", "END", "end" };
    inline constexpr std::size_t MAX_INI_DEPTH = 16;

    /**
     * @brief Checks whether a token matches any valid SAGE block closing keyword ("End", "END", "end").
     */
    [[nodiscard]] constexpr bool is_ini_end(std::string_view token) noexcept {
        for (const auto end_kw : INI_ENDS) {
            if (token == end_kw) {
                return true;
            }
        }
        return false;
    }

    /**
     * @brief Represents a standalone or block-internal comment.
     */
    struct CommentNode {
        std::string text{};

        [[nodiscard]] bool operator==(const CommentNode&) const = default;
    };

    /**
     * @brief Represents a standard property assignment or value line.
     */
    struct StatementNode {
        std::string text{};
        std::string comment{};

        [[nodiscard]] bool operator==(const StatementNode&) const = default;
    };

    /**
     * @brief Represents a #include preprocessor directive.
     */
    struct IncludeNode {
        std::string raw_path{};
        std::string comment{};

        /**
         * @brief Returns normalized path with surrounding whitespace/quotes stripped and forward slashes.
         */
        [[nodiscard]] std::string clean_path() const {
            constexpr std::string_view strip_chars = " \t\"'";
            std::string_view view{ raw_path };

            const auto first = view.find_first_not_of(strip_chars);
            if (first == std::string_view::npos) {
                return {};
            }
            const auto last = view.find_last_not_of(strip_chars);
            view = view.substr(first, last - first + 1);

            std::string normalized{ view };
            std::ranges::replace(normalized, '\\', '/');
            return normalized;
        }

        [[nodiscard]] bool operator==(const IncludeNode&) const = default;
    };

    /**
     * @brief Represents an opaque embedded script block (BeginScript ... EndScript).
     */
    struct ScriptNode {
        std::string name{ "BeginScript" };
        std::string identifier{};
        std::string comment{};
        std::string header_comment{};
        std::string end_token{ "EndScript" };
        std::string end_comment{};
        std::vector<std::string> content{};

        [[nodiscard]] std::string print(int level = 0, std::string_view file_type = ".ini") const;

        [[nodiscard]] bool operator==(const ScriptNode&) const = default;
    };

    struct ConstructLevel;

    /**
     * @brief Polymorphic value variant representing any node within an INI/INC hierarchy.
     */
    using AstNode = std::variant<
        CommentNode,
        StatementNode,
        IncludeNode,
        ScriptNode,
        ConstructLevel
    >;

    /**
     * @brief Represents an inner block or defined object within a parsed SAGE configuration file.
     */
    struct ConstructLevel {
        std::string _class;
        std::string name;
        std::string identifier;
        std::string comment;
        std::string header_comment;
        std::string end_token;
        std::string end_comment;
        std::vector<AstNode> items;

        ConstructLevel();
        explicit ConstructLevel(
            std::string cls,
            std::string blk_name = {},
            std::string ident = {},
            std::string cmt = {},
            std::string hdr_cmt = {},
            std::string end_tok = {},
            std::string end_cmt = {}
        );
        ~ConstructLevel();

        ConstructLevel(const ConstructLevel&);
        ConstructLevel& operator=(const ConstructLevel&);
        ConstructLevel(ConstructLevel&&) noexcept;
        ConstructLevel& operator=(ConstructLevel&&) noexcept;

        [[nodiscard]] std::size_t size() const noexcept { return items.size(); }
        [[nodiscard]] bool empty() const noexcept { return items.empty(); }

        void append(AstNode item) { items.push_back(std::move(item)); }

        [[nodiscard]] AstNode& operator[](std::size_t index) { return items[index]; }
        [[nodiscard]] const AstNode& operator[](std::size_t index) const { return items[index]; }

        [[nodiscard]] auto begin() noexcept { return items.begin(); }
        [[nodiscard]] auto end() noexcept { return items.end(); }
        [[nodiscard]] auto begin() const noexcept { return items.begin(); }
        [[nodiscard]] auto end() const noexcept { return items.end(); }
        [[nodiscard]] auto cbegin() const noexcept { return items.cbegin(); }
        [[nodiscard]] auto cend() const noexcept { return items.cend(); }

        [[nodiscard]] std::string print(int level = 0, std::string_view file_type = ".ini") const;

        [[nodiscard]] bool operator==(const ConstructLevel&) const = default;
    };

    inline ConstructLevel::ConstructLevel() = default;

    inline ConstructLevel::ConstructLevel(
        std::string cls,
        std::string blk_name,
        std::string ident,
        std::string cmt,
        std::string hdr_cmt,
        std::string end_tok,
        std::string end_cmt
    )
        : _class(std::move(cls)),
        name(std::move(blk_name)),
        identifier(std::move(ident)),
        comment(std::move(cmt)),
        header_comment(std::move(hdr_cmt)),
        end_token(std::move(end_tok)),
        end_comment(std::move(end_cmt)) {
    }

    inline ConstructLevel::~ConstructLevel() = default;
    inline ConstructLevel::ConstructLevel(const ConstructLevel&) = default;
    inline ConstructLevel& ConstructLevel::operator=(const ConstructLevel&) = default;
    inline ConstructLevel::ConstructLevel(ConstructLevel&&) noexcept = default;
    inline ConstructLevel& ConstructLevel::operator=(ConstructLevel&&) noexcept = default;

    /**
     * @brief Child node variant allowed inside a localized .str entry.
     */
    using StrChildNode = std::variant<CommentNode, StatementNode>;

    /**
     * @brief Represents a single localized string entry inside a SAGE .str file.
     */
    struct StrEntry {
        std::string category{};
        std::string identifier{};
        std::string comment{};
        std::string header_comment{};
        std::string end_token{ "End" };
        std::string end_comment{};
        std::vector<StrChildNode> items{};

        [[nodiscard]] std::string print() const;

        [[nodiscard]] bool operator==(const StrEntry&) const = default;
    };

    /**
     * @brief Top-level entry variant for SAGE .str localization documents.
     */
    using StrDocEntry = std::variant<StrEntry, CommentNode, StatementNode>;

    /**
     * @brief Flat AST representation for SAGE .str localization files.
     */
    struct StrDocument {
        std::string name{};
        std::vector<StrDocEntry> entries{};
        std::vector<std::string> errors{};

        [[nodiscard]] std::string print() const;
    };

    /**
     * @brief Top-level item variant stored in ConstructFile (supports both INI/INC AST nodes and STR entries).
     */
    using RootItem = std::variant<AstNode, StrEntry>;

    /**
     * @brief Non-owning pointer variant referencing any serializable AST node without copying.
     */
    using SerializableNodeRef = std::variant<
        const CommentNode*,
        const StatementNode*,
        const IncludeNode*,
        const ScriptNode*,
        const ConstructLevel*,
        const StrEntry*
    >;

    /**
     * @brief Explicit stack frame used by the iterative AST serializer to avoid call-stack recursion.
     */
    struct SerializationFrame {
        SerializableNodeRef node;
        int level{ 0 };
        bool is_closing{ false };
    };

    /**
     * @brief Converts an AstNode reference into a non-owning SerializableNodeRef.
     */
    [[nodiscard]] inline SerializableNodeRef to_serializable_ref(const AstNode& node) noexcept {
        return std::visit([](const auto& concrete) -> SerializableNodeRef {
            return &concrete;
            }, node);
    }

    /**
     * @brief Converts a StrChildNode reference into a non-owning SerializableNodeRef.
     */
    [[nodiscard]] inline SerializableNodeRef to_serializable_ref(const StrChildNode& node) noexcept {
        return std::visit([](const auto& concrete) -> SerializableNodeRef {
            return &concrete;
            }, node);
    }

    /**
     * @brief Converts a StrDocEntry reference into a non-owning SerializableNodeRef.
     */
    [[nodiscard]] inline SerializableNodeRef to_serializable_ref(const StrDocEntry& node) noexcept {
        return std::visit([](const auto& concrete) -> SerializableNodeRef {
            return &concrete;
            }, node);
    }

    /**
     * @brief Converts a RootItem reference into a non-owning SerializableNodeRef.
     */
    [[nodiscard]] inline SerializableNodeRef to_serializable_ref(const RootItem& item) noexcept {
        return std::visit([](const auto& concrete) -> SerializableNodeRef {
            using T = std::decay_t<decltype(concrete)>;
            if constexpr (std::is_same_v<T, AstNode>) {
                return to_serializable_ref(concrete);
            }
            else {
                return &concrete;
            }
            }, item);
    }

} // namespace lotm::ini
