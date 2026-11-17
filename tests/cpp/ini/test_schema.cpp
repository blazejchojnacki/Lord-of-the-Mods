/**
 * @file tests/cpp/ini/test_schema.cpp
 * @brief Unit tests for compile-time and runtime delimiter schema rules in lotm::ini.
 *
 * Copyright (c) 2026 Błażej Chojnacki <blazej.chojnacki@outlook.com>
 * Part of the Lord of the Mods (lotm) project.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <catch2/catch_test_macros.hpp>
#include "ini/schema.hpp"
#include "ini/lexer.hpp"
#include <vector>
#include <string>

using namespace lotm::ini;

TEST_CASE("Compile-time and runtime delimiter schema rules", "[ini][schema]") {
    SECTION("compile_delimiter_rule handles operators, whitespace, and MAX_RULE_TOKENS cap") {
        constexpr auto eq_rule = compile_delimiter_rule("AddEmotion = OVERRIDE");
        STATIC_REQUIRE(eq_rule.token_count == 3);
        STATIC_REQUIRE(eq_rule.word_count == 2);
        STATIC_REQUIRE(eq_rule.tokens().size() == 3);
        STATIC_REQUIRE(eq_rule.tokens()[0] == "AddEmotion");
        STATIC_REQUIRE(eq_rule.tokens()[1] == "=");
        STATIC_REQUIRE(eq_rule.tokens()[2] == "OVERRIDE");

        constexpr auto colon_rule = compile_delimiter_rule("  CONTROLBAR : Button  ");
        STATIC_REQUIRE(colon_rule.token_count == 3);
        STATIC_REQUIRE(colon_rule.word_count == 2);
        STATIC_REQUIRE(colon_rule.tokens()[1] == ":");

        constexpr auto empty_rule = compile_delimiter_rule("   \t\r\n ");
        STATIC_REQUIRE(empty_rule.token_count == 0);
        STATIC_REQUIRE(empty_rule.word_count == 0);

        constexpr auto overflow_rule = compile_delimiter_rule("A = B : C = D : E = F");
        STATIC_REQUIRE(overflow_rule.token_count == MAX_RULE_TOKENS);
        STATIC_REQUIRE(overflow_rule.word_count == 6);
    }

    SECTION("compile_delimiter_rules sorts descending by token count and skips empty rules") {
        const std::vector<std::string> raw_list = {
            "SingleToken",
            "   ",
            "Three = Tokens",
            "Two Tokens"
        };
        const auto compiled = compile_delimiter_rules(raw_list);
        REQUIRE(compiled.size() == 3);
        CHECK(compiled[0].raw == "Three = Tokens");
        CHECK(compiled[1].raw == "Two Tokens");
        CHECK(compiled[2].raw == "SingleToken");
    }

    SECTION("match_delimiter_rule matches case-insensitively and rejects partial tokens") {
        const std::vector<std::string> raw_list = { "AddEmotion = OVERRIDE", "Behavior" };
        const auto rules = compile_delimiter_rules(raw_list);

        const auto lex1 = lex_line("addemotion = override ModuleTag_01");
        const DelimiterRule* m1 = match_delimiter_rule(lex1.line_tokens, rules);
        REQUIRE(m1 != nullptr);
        CHECK(m1->raw == "AddEmotion = OVERRIDE");

        const auto lex2 = lex_line("AddEmotion = DIFFERENT");
        CHECK(match_delimiter_rule(lex2.line_tokens, rules) == nullptr);

        const auto lex3 = lex_line("");
        CHECK(match_delimiter_rule(lex3.line_tokens, rules) == nullptr);
    }
}
