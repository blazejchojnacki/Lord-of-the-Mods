/**
 * @file src/ini/ast.cpp
 * @brief Implementation of ConstructLevel and ConstructFile AST query, search, and mutation methods.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "ini/parser.hpp"
#include "ini/lexer.hpp"
#include "parser_utils.hpp"

#include <algorithm>
#include <stdexcept>

namespace lotm::ini {

    namespace {

        [[nodiscard]] constexpr AstNode* as_ast_node(AstNode& item) noexcept {
            return &item;
        }

        [[nodiscard]] constexpr const AstNode* as_ast_node(const AstNode& item) noexcept {
            return &item;
        }

        [[nodiscard]] constexpr AstNode* as_ast_node(RootItem& item) noexcept {
            return std::get_if<AstNode>(&item);
        }

        [[nodiscard]] constexpr const AstNode* as_ast_node(const RootItem& item) noexcept {
            return std::get_if<AstNode>(&item);
        }

        [[nodiscard]] std::vector<std::string_view> tokenize_class_spec(std::string_view spec) {
            std::vector<std::string_view> tokens;
            std::size_t pos = 0;
            const std::size_t len = spec.size();

            while (pos < len) {
                while (pos < len && detail::is_lex_space(spec[pos])) {
                    ++pos;
                }
                if (pos >= len) {
                    break;
                }
                if (spec[pos] == '=') {
                    tokens.push_back("=");
                    ++pos;
                }
                else {
                    const std::size_t start = pos;
                    while (pos < len && !detail::is_lex_space(spec[pos]) && spec[pos] != '=') {
                        ++pos;
                    }
                    tokens.push_back(spec.substr(start, pos - start));
                }
            }

            if (!tokens.empty() && tokens.back() == "=") {
                tokens.pop_back();
            }
            return tokens;
        }

        [[nodiscard]] bool matches_class_spec(std::string_view node_class, std::string_view query_class) {
            const auto node_tokens = tokenize_class_spec(node_class);
            const auto query_tokens = tokenize_class_spec(query_class);
            if (node_tokens.size() != query_tokens.size()) {
                return false;
            }
            for (std::size_t i = 0; i < node_tokens.size(); ++i) {
                if (!detail::iequals_ascii(node_tokens[i], query_tokens[i])) {
                    return false;
                }
            }
            return true;
        }

        [[nodiscard]] bool matches_block_criteria(
            const ConstructLevel& lvl,
            std::string_view block_class,
            std::optional<std::string_view> block_name,
            std::optional<std::string_view> block_identifier
        ) {
            if (!matches_class_spec(lvl._class, block_class)) {
                return false;
            }
            if (block_name.has_value() &&
                !detail::iequals_ascii(detail::trim_view(lvl.name), detail::trim_view(*block_name))) {
                return false;
            }
            if (block_identifier.has_value() &&
                !detail::iequals_ascii(
                    detail::collapse_whitespace(lvl.identifier),
                    detail::collapse_whitespace(*block_identifier)
                )) {
                return false;
            }
            return true;
        }

        struct ParsedStatementView {
            std::string_view key{};
            std::string_view value{};
            std::size_t key_start{ 0 };
            std::size_t key_end{ 0 };
            std::size_t eq_pos{ std::string_view::npos };
            std::size_t value_start{ std::string_view::npos };
        };

        [[nodiscard]] std::optional<ParsedStatementView> parse_statement_key_value(std::string_view text) noexcept {
            std::size_t pos = 0;
            const std::size_t len = text.size();
            while (pos < len && detail::is_lex_space(text[pos])) {
                ++pos;
            }
            if (pos >= len) {
                return std::nullopt;
            }

            std::size_t k_end = pos;
            while (k_end < len && !detail::is_lex_space(text[k_end]) && text[k_end] != '=') {
                ++k_end;
            }

            ParsedStatementView parsed;
            parsed.key = text.substr(pos, k_end - pos);
            parsed.key_start = pos;
            parsed.key_end = k_end;

            std::size_t sep_pos = k_end;
            while (sep_pos < len && detail::is_lex_space(text[sep_pos])) {
                ++sep_pos;
            }

            if (sep_pos < len && text[sep_pos] == '=') {
                parsed.eq_pos = sep_pos;
                std::size_t v_start = sep_pos + 1;
                while (v_start < len && detail::is_lex_space(text[v_start])) {
                    ++v_start;
                }
                parsed.value_start = v_start;
                parsed.value = detail::rstrip_view(text.substr(v_start));
            }
            else if (sep_pos < len) {
                parsed.value_start = sep_pos;
                parsed.value = detail::rstrip_view(text.substr(sep_pos));
            }
            else {
                parsed.value_start = len;
                parsed.value = std::string_view{};
            }

            return parsed;
        }

        void apply_statement_value(StatementNode& stmt, const ParsedStatementView& parsed, std::string_view new_value) {
            const std::string_view orig = stmt.text;
            if (parsed.eq_pos != std::string_view::npos) {
                if (parsed.value_start < orig.size()) {
                    std::string updated;
                    updated.reserve(parsed.value_start + new_value.size());
                    updated.append(orig.substr(0, parsed.value_start));
                    updated.append(new_value);
                    stmt.text = std::move(updated);
                }
                else {
                    std::string updated{ orig.substr(0, parsed.eq_pos + 1) };
                    if (!new_value.empty()) {
                        if (parsed.eq_pos > parsed.key_end) {
                            updated.push_back(' ');
                        }
                        updated.append(new_value);
                    }
                    stmt.text = std::move(updated);
                }
            }
            else if (parsed.value_start < orig.size()) {
                std::string updated;
                updated.reserve(parsed.value_start + new_value.size());
                updated.append(orig.substr(0, parsed.value_start));
                updated.append(new_value);
                stmt.text = std::move(updated);
            }
            else {
                std::string updated{ parsed.key };
                if (!new_value.empty()) {
                    updated.append(" = ");
                    updated.append(new_value);
                }
                stmt.text = std::move(updated);
            }
        }

        template <typename ItemT, typename OnMatchFn>
        void traverse_matching_blocks(
            StableVector<ItemT>& items,
            std::string_view block_class,
            std::optional<std::string_view> block_name,
            std::optional<std::string_view> block_identifier,
            bool recursive,
            OnMatchFn&& on_match
        ) {
            if (!recursive) {
                for (auto& item : items) {
                    if (auto* ast = as_ast_node(item)) {
                        if (auto* lvl = std::get_if<ConstructLevel>(ast)) {
                            if (matches_block_criteria(*lvl, block_class, block_name, block_identifier)) {
                                if (!on_match(lvl)) {
                                    return;
                                }
                            }
                        }
                    }
                }
                return;
            }

            std::vector<ConstructLevel*> stack;
            for (auto it = items.rbegin(); it != items.rend(); ++it) {
                if (auto* ast = as_ast_node(*it)) {
                    if (auto* lvl = std::get_if<ConstructLevel>(ast)) {
                        stack.push_back(lvl);
                    }
                }
            }

            while (!stack.empty()) {
                ConstructLevel* current = stack.back();
                stack.pop_back();

                if (matches_block_criteria(*current, block_class, block_name, block_identifier)) {
                    if (!on_match(current)) {
                        return;
                    }
                }

                for (auto it = current->items.rbegin(); it != current->items.rend(); ++it) {
                    if (auto* child_lvl = std::get_if<ConstructLevel>(&(*it))) {
                        stack.push_back(child_lvl);
                    }
                }
            }
        }

        template <typename ItemT>
        [[nodiscard]] ConstructLevel* find_block_impl(
            StableVector<ItemT>& items,
            std::string_view block_class,
            std::optional<std::string_view> block_name,
            std::optional<std::string_view> block_identifier,
            bool recursive
        ) {
            ConstructLevel* found = nullptr;
            traverse_matching_blocks(items, block_class, block_name, block_identifier, recursive,
                [&](ConstructLevel* match) noexcept {
                    found = match;
                    return false;
                });
            return found;
        }

        template <typename ItemT>
        [[nodiscard]] std::vector<ConstructLevel*> find_all_impl(
            StableVector<ItemT>& items,
            std::string_view block_class,
            std::optional<std::string_view> block_name,
            std::optional<std::string_view> block_identifier,
            bool recursive
        ) {
            std::vector<ConstructLevel*> matches;
            traverse_matching_blocks(items, block_class, block_name, block_identifier, recursive,
                [&](ConstructLevel* match) {
                    matches.push_back(match);
                    return true;
                });
            return matches;
        }

        template <typename ItemT>
        [[nodiscard]] std::optional<std::string> get_value_impl(
            const StableVector<ItemT>& items,
            std::string_view key
        ) {
            const std::string_view trimmed_key = detail::trim_view(key);
            if (trimmed_key.empty()) {
                return std::nullopt;
            }

            std::optional<std::string> last_match;
            for (const auto& item : items) {
                if (const auto* ast = as_ast_node(item)) {
                    if (const auto* stmt = std::get_if<StatementNode>(ast)) {
                        if (const auto parsed = parse_statement_key_value(stmt->text)) {
                            if (detail::iequals_ascii(parsed->key, trimmed_key)) {
                                last_match = std::string{ parsed->value };
                            }
                        }
                    }
                }
            }
            return last_match;
        }

        template <typename ItemT>
        [[nodiscard]] std::vector<std::string> get_all_values_impl(
            const StableVector<ItemT>& items,
            std::string_view key
        ) {
            std::vector<std::string> values;
            const std::string_view trimmed_key = detail::trim_view(key);
            if (trimmed_key.empty()) {
                return values;
            }

            for (const auto& item : items) {
                if (const auto* ast = as_ast_node(item)) {
                    if (const auto* stmt = std::get_if<StatementNode>(ast)) {
                        if (const auto parsed = parse_statement_key_value(stmt->text)) {
                            if (detail::iequals_ascii(parsed->key, trimmed_key)) {
                                values.emplace_back(parsed->value);
                            }
                        }
                    }
                }
            }
            return values;
        }

        template <typename ItemT>
        void set_value_impl(
            StableVector<ItemT>& items,
            std::string_view key,
            std::string_view value
        ) {
            const std::string_view trimmed_key = detail::trim_view(key);
            if (trimmed_key.empty()) {
                throw std::invalid_argument("Property key cannot be empty.");
            }
            for (const char c : trimmed_key) {
                if (detail::is_lex_space(c) || c == '=' || c == ':' || c == '\r' || c == '\n') {
                    throw std::invalid_argument("Property key contains invalid whitespace or separator characters.");
                }
            }
            for (const char c : value) {
                if (c == '\r' || c == '\n') {
                    throw std::invalid_argument("Property value cannot contain newline characters.");
                }
            }
            validate_sage_bounds(trimmed_key, value);

            StatementNode* target_stmt = nullptr;
            ParsedStatementView target_parsed;

            for (auto& item : items) {
                if (auto* ast = as_ast_node(item)) {
                    if (auto* stmt = std::get_if<StatementNode>(ast)) {
                        if (const auto parsed = parse_statement_key_value(stmt->text)) {
                            if (detail::iequals_ascii(parsed->key, trimmed_key)) {
                                target_stmt = stmt;
                                target_parsed = *parsed;
                            }
                        }
                    }
                }
            }

            if (target_stmt != nullptr) {
                apply_statement_value(*target_stmt, target_parsed, value);
                return;
            }

            std::string new_line{ trimmed_key };
            if (value.empty()) {
                new_line.append(" =");
            }
            else {
                new_line.append(" = ");
                new_line.append(value);
            }
            items.emplace_back(AstNode{ StatementNode{ std::move(new_line), "" } });
        }

        template <typename ItemT>
        [[nodiscard]] bool remove_value_impl(
            StableVector<ItemT>& items,
            std::string_view key,
            bool all_occurrences
        ) {
            const std::string_view trimmed_key = detail::trim_view(key);
            if (trimmed_key.empty()) {
                return false;
            }

            bool removed_any = false;
            for (std::size_t i = items.size(); i > 0; --i) {
                const std::size_t idx = i - 1;
                if (const auto* ast = as_ast_node(items[idx])) {
                    if (const auto* stmt = std::get_if<StatementNode>(ast)) {
                        if (const auto parsed = parse_statement_key_value(stmt->text)) {
                            if (detail::iequals_ascii(parsed->key, trimmed_key)) {
                                items.erase_at(idx);
                                removed_any = true;
                                if (!all_occurrences) {
                                    return true;
                                }
                            }
                        }
                    }
                }
            }
            return removed_any;
        }

        template <typename ItemT>
        [[nodiscard]] bool remove_block_impl(
            StableVector<ItemT>& items,
            std::string_view block_class,
            std::optional<std::string_view> block_name,
            std::optional<std::string_view> block_identifier
        ) {
            for (std::size_t i = 0; i < items.size(); ++i) {
                if (const auto* ast = as_ast_node(items[i])) {
                    if (const auto* lvl = std::get_if<ConstructLevel>(ast)) {
                        if (matches_block_criteria(*lvl, block_class, block_name, block_identifier)) {
                            items.erase_at(i);
                            return true;
                        }
                    }
                }
            }
            return false;
        }

    } // namespace

    ConstructLevel* ConstructLevel::find_block(
        std::string_view block_class,
        std::optional<std::string_view> block_name,
        std::optional<std::string_view> block_identifier,
        bool recursive
    ) {
        return find_block_impl(items, block_class, block_name, block_identifier, recursive);
    }

    const ConstructLevel* ConstructLevel::find_block(
        std::string_view block_class,
        std::optional<std::string_view> block_name,
        std::optional<std::string_view> block_identifier,
        bool recursive
    ) const {
        return const_cast<ConstructLevel*>(this)->find_block(block_class, block_name, block_identifier, recursive);
    }

    std::vector<ConstructLevel*> ConstructLevel::find_all(
        std::string_view block_class,
        std::optional<std::string_view> block_name,
        std::optional<std::string_view> block_identifier,
        bool recursive
    ) {
        return find_all_impl(items, block_class, block_name, block_identifier, recursive);
    }

    std::vector<const ConstructLevel*> ConstructLevel::find_all(
        std::string_view block_class,
        std::optional<std::string_view> block_name,
        std::optional<std::string_view> block_identifier,
        bool recursive
    ) const {
        auto mutable_matches = const_cast<ConstructLevel*>(this)->find_all(
            block_class, block_name, block_identifier, recursive
        );
        return std::vector<const ConstructLevel*>(mutable_matches.begin(), mutable_matches.end());
    }

    std::optional<std::string> ConstructLevel::get_value(std::string_view key) const {
        return get_value_impl(items, key);
    }

    std::vector<std::string> ConstructLevel::get_all_values(std::string_view key) const {
        return get_all_values_impl(items, key);
    }

    void ConstructLevel::set_value(std::string_view key, std::string_view value) {
        set_value_impl(items, key, value);
    }

    bool ConstructLevel::remove_value(std::string_view key, bool all_occurrences) {
        return remove_value_impl(items, key, all_occurrences);
    }

    bool ConstructLevel::remove_block(
        std::string_view block_class,
        std::optional<std::string_view> block_name,
        std::optional<std::string_view> block_identifier
    ) {
        return remove_block_impl(items, block_class, block_name, block_identifier);
    }

    ConstructLevel* ConstructFile::find_block(
        std::string_view block_class,
        std::optional<std::string_view> block_name,
        std::optional<std::string_view> block_identifier,
        bool recursive
    ) {
        return find_block_impl(items, block_class, block_name, block_identifier, recursive);
    }

    const ConstructLevel* ConstructFile::find_block(
        std::string_view block_class,
        std::optional<std::string_view> block_name,
        std::optional<std::string_view> block_identifier,
        bool recursive
    ) const {
        return const_cast<ConstructFile*>(this)->find_block(block_class, block_name, block_identifier, recursive);
    }

    std::vector<ConstructLevel*> ConstructFile::find_all(
        std::string_view block_class,
        std::optional<std::string_view> block_name,
        std::optional<std::string_view> block_identifier,
        bool recursive
    ) {
        return find_all_impl(items, block_class, block_name, block_identifier, recursive);
    }

    std::vector<const ConstructLevel*> ConstructFile::find_all(
        std::string_view block_class,
        std::optional<std::string_view> block_name,
        std::optional<std::string_view> block_identifier,
        bool recursive
    ) const {
        auto mutable_matches = const_cast<ConstructFile*>(this)->find_all(
            block_class, block_name, block_identifier, recursive
        );
        return std::vector<const ConstructLevel*>(mutable_matches.begin(), mutable_matches.end());
    }

    std::optional<std::string> ConstructFile::get_value(std::string_view key) const {
        return get_value_impl(items, key);
    }

    std::vector<std::string> ConstructFile::get_all_values(std::string_view key) const {
        return get_all_values_impl(items, key);
    }

    void ConstructFile::set_value(std::string_view key, std::string_view value) {
        set_value_impl(items, key, value);
    }

    bool ConstructFile::remove_value(std::string_view key, bool all_occurrences) {
        return remove_value_impl(items, key, all_occurrences);
    }

    bool ConstructFile::remove_block(
        std::string_view block_class,
        std::optional<std::string_view> block_name,
        std::optional<std::string_view> block_identifier
    ) {
        return remove_block_impl(items, block_class, block_name, block_identifier);
    }

} // namespace lotm::ini
